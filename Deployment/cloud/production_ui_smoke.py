#!/usr/bin/env python3
"""SarembokVE production smoke test.

Run on the VPS after pulling main. It validates the public shell, browser session,
WebSocket JSON-RPC, provider response metadata, browser worker, theme control,
navigation, and basic Execute UI behavior.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from textwrap import dedent

BASE = "https://sarembok.com"


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def http_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"Accept": "text/html", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")


def run_in_container(container: str, code: str) -> str:
    proc = subprocess.run(
        ["docker", "exec", container, "python", "-c", code],
        text=True,
        capture_output=True,
        timeout=90,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{container}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


def main() -> int:
    failures: list[str] = []

    print("===== SAREMBOKVE PRODUCTION UI SMOKE =====")

    try:
        health = urllib.request.urlopen(f"{BASE}/health", timeout=10).read().decode().strip()
        print("[PASS] public health:", health)
        if health != "OK":
            failures.append("public health is not OK")
    except Exception as exc:
        failures.append(f"public health: {exc}")

    try:
        session = http_json(f"{BASE}/session")
        token = session.get("sessionToken")
        if not token:
            raise RuntimeError("no sessionToken")
        print("[PASS] /session: token issued; expiresIn=", session.get("expiresIn"))
        required = {"SarembokChat", "GetRuntimeInfo", "ListTasks", "BrowserRender", "BrowserScreenshot"}
        missing = sorted(required - set(session.get("scope", [])))
        if missing:
            failures.append("session scope missing: " + ", ".join(missing))
    except Exception as exc:
        failures.append(f"/session: {exc}")

    try:
        html = http_text(BASE + "/")
        checks = {
            "full_frontend": "SAREMBOKVE" in html and "dock-btn-dialogue" in html,
            "runtime_shell": "runtime-ui-repair.js" in html,
            "theme_control": "srbk-theme-toggle" in html and "SAREMBOK_THEME_CONTROL_V1_20260916" in html,
            "markdown_renderer": "function md(text)" in html and "SAREMBOK_MD_NORMALIZATION_20260914" in html,
            "stable_not_root": "AI-NATIVE COMPUTING ENVIRONMENT" in html and "One control surface. Live runtime state." not in html,
        }
        for name, ok in checks.items():
            print(f"[{'PASS' if ok else 'FAIL'}] public HTML {name}")
            if not ok:
                failures.append(f"public HTML {name}")
    except Exception as exc:
        failures.append(f"public root HTML: {exc}")

    ws_code = dedent('''
        import asyncio, json, urllib.request, websockets
        token = json.load(urllib.request.urlopen("http://127.0.0.1:9000/session", timeout=5))["sessionToken"]

        async def main():
            async with websockets.connect("ws://127.0.0.1:9000/ws", open_timeout=8, close_timeout=5, ping_interval=20, ping_timeout=20) as ws:
                async def rpc(i, method, params=None):
                    await ws.send(json.dumps({"jsonrpc":"2.0","id":i,"method":method,"params":dict(params or {}, sessionToken=token)}))
                    while True:
                        data = json.loads(await ws.recv())
                        if data.get("id") == i:
                            if data.get("error"):
                                raise RuntimeError(data["error"].get("message"))
                            return data.get("result")

                info = await rpc("runtime", "GetRuntimeInfo")
                chat = await rpc("chat", "SarembokChat", {"prompt":"Reply with exactly READY","stream":False,"sessionId":"production-smoke"})
                browser = await rpc("browser", "BrowserRender", {"url":"https://sarembok.com"})
                tasks = await rpc("tasks", "ListTasks")
                print(json.dumps({
                    "runtime_status": info.get("status"),
                    "workers_online": info.get("onlineWorkers"),
                    "memory_count": info.get("totalMemories"),
                    "chat_source": chat.get("source"),
                    "chat_model": chat.get("model"),
                    "chat_response_present": bool(chat.get("response")),
                    "browser_render_ok": bool(browser.get("ok") or browser.get("html") or browser.get("title")),
                    "task_count": tasks.get("count"),
                }, sort_keys=True))

        asyncio.run(main())
    ''')

    try:
        out = run_in_container("sarembok-runtime", ws_code)
        data = json.loads(out)
        print("[PASS] session -> WebSocket -> JSON-RPC")
        print("       provider=", data.get("chat_source"), "model=", data.get("chat_model"))
        if not data.get("chat_response_present"):
            failures.append("SarembokChat returned no response")
        if not data.get("browser_render_ok"):
            failures.append("BrowserRender returned no usable result")
    except Exception as exc:
        failures.append(f"runtime WebSocket/RPC/provider/browser path: {exc}")

    try:
        browser_health = run_in_container("sarembok-browser", 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:9100/health", timeout=5).read().decode().strip())')
        print("[PASS] browser worker 9100:", browser_health)
        if browser_health != "OK":
            failures.append("browser worker health is not OK")
    except Exception as exc:
        failures.append(f"browser worker 9100: {exc}")

    playwright_code = dedent('''
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto("https://sarembok.com/", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1500)
            health = page.evaluate("window.__srbkRuntimeUiHealth || null")
            if not health:
                raise RuntimeError("runtime UI health snapshot missing")
            if not health.get("rpcRecovery"):
                raise RuntimeError("rpc recovery wrapper not installed")
            if not health.get("navigation"):
                raise RuntimeError("navigation health failed")
            if not health.get("markdownRenderer"):
                raise RuntimeError("markdown renderer health failed")
            theme = page.locator("#srbk-theme-toggle")
            if theme.count() != 1:
                raise RuntimeError(f"expected one theme control, found {theme.count()}")
            before = page.locator("html").get_attribute("data-theme")
            theme.click()
            page.wait_for_timeout(100)
            after = page.locator("html").get_attribute("data-theme")
            theme.click()
            page.wait_for_timeout(100)
            restored = page.locator("html").get_attribute("data-theme")
            if before == after or before != restored:
                raise RuntimeError(f"theme toggle failed: {before} -> {after} -> {restored}")
            nav_ids = page.locator(".dock-btn").evaluate_all("els => els.map(e => e.id.replace(/^dock-btn-/, ''))")
            for tab in nav_ids:
                page.locator(f"#dock-btn-{tab}").click()
                page.wait_for_timeout(100)
                if not page.locator(f"#view-{tab}.active").count():
                    raise RuntimeError(f"tab did not activate: {tab}")
            print({"health": health, "theme": [before, after, restored], "tabs": nav_ids})
            browser.close()
    ''')
    try:
        out = run_in_container("sarembok-browser", playwright_code)
        print("[PASS] Playwright UI navigation + theme:", out)
    except Exception as exc:
        failures.append(f"Playwright UI navigation/theme: {exc}")

    print("===== RESULT =====")
    if failures:
        for failure in failures:
            print("[FAIL]", failure)
        return 1
    print("[PASS] ALL PRODUCTION UI SMOKE CHECKS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
