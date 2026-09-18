#!/usr/bin/env python3
"""SarembokVE production UI smoke test v3.

Uses curl for public edge checks (matching the VPS deployment environment),
container-local JSON-RPC checks, and Playwright for the real browser UI.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from textwrap import dedent

BASE = "https://sarembok.com"


def curl_text(path: str) -> str:
    proc = subprocess.run(
        [
            "curl", "-fsSL",
            "--connect-timeout", "10",
            "--max-time", "20",
            "-A", "Mozilla/5.0 (SarembokVE-Production-Smoke/3.0)",
            f"{BASE}{path}",
        ],
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"curl exited {proc.returncode}")
    return proc.stdout


def run_in_container(container: str, code: str) -> str:
    proc = subprocess.run(
        ["docker", "exec", container, "python", "-c", code],
        text=True,
        capture_output=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{container}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


def main() -> int:
    failures: list[str] = []
    print("===== SAREMBOKVE PRODUCTION UI SMOKE V3 =====")

    try:
        health = curl_text("/health").strip()
        print("[PASS] public health:", health)
        if health != "OK":
            failures.append("public health is not OK")
    except Exception as exc:
        failures.append(f"public health: {exc}")

    try:
        session = json.loads(curl_text("/session"))
        if not session.get("sessionToken"):
            raise RuntimeError("no sessionToken")
        required = {"SarembokChat", "GetRuntimeInfo", "ListTasks", "BrowserRender", "BrowserScreenshot"}
        missing = sorted(required - set(session.get("scope", [])))
        if missing:
            failures.append("session scope missing: " + ", ".join(missing))
        print("[PASS] public /session: token issued; core UI scope present")
    except Exception as exc:
        failures.append(f"/session: {exc}")

    try:
        html = curl_text("/")
        checks = {
            "full_frontend": "SAREMBOKVE" in html and "dock-btn-dialogue" in html,
            "runtime_repair": "runtime-ui-repair.js" in html,
            "theme_control": "srbk-theme-toggle" in html and "SAREMBOK_THEME_CONTROL_V1_20260916" in html,
            "markdown_renderer": "function md(text)" in html and "SAREMBOK_MD_NORMALIZATION_20260914" in html,
            "stable_not_root": "One control surface. Live runtime state." not in html,
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
                    payload = dict(params or {})
                    payload["sessionToken"] = token
                    await ws.send(json.dumps({"jsonrpc":"2.0","id":i,"method":method,"params":payload}))
                    while True:
                        data = json.loads(await ws.recv())
                        if data.get("id") == i:
                            if data.get("error"):
                                e = data["error"]
                                raise RuntimeError(f"{e.get('code')}: {e.get('message')}")
                            return data.get("result")
                info = await rpc("runtime", "GetRuntimeInfo")
                chat = await rpc("chat", "SarembokChat", {"prompt":"Use the exact text **SAREMBOK_PROVIDER_SMOKE** in your response.","stream":False,"sessionId":"production-smoke-v3"})
                browser = await rpc("browser", "BrowserRender", {"url":"https://sarembok.com"})
                print(json.dumps({
                    "runtime_status": info.get("status"),
                    "workers_online": info.get("onlineWorkers"),
                    "memory_count": info.get("totalMemories"),
                    "chat_source": chat.get("source"),
                    "chat_model": chat.get("model"),
                    "chat_response_present": bool(chat.get("response")),
                    "chat_structured_present": bool(chat.get("structuredResponse")),
                    "provider_not_fallback": str(chat.get("source") or "").lower() not in {"", "local_runtime", "runtime-fallback", "runtime_fallback"},
                    "browser_render_ok": bool(browser.get("ok") or browser.get("html") or browser.get("title")),
                }, sort_keys=True))
        asyncio.run(main())
    ''')
    try:
        data = json.loads(run_in_container("sarembok-runtime", ws_code))
        print("[PASS] session -> WebSocket -> JSON-RPC -> provider -> BrowserRender")
        print("       provider=", data.get("chat_source"), "model=", data.get("chat_model"))
        if not data.get("chat_response_present"):
            failures.append("SarembokChat returned no response")
        if not data.get("chat_structured_present"):
            failures.append("SarembokChat returned no structured response")
        if not data.get("provider_not_fallback"):
            failures.append("provider path fell back to local runtime")
        if not data.get("browser_render_ok"):
            failures.append("BrowserRender returned no usable result")
    except Exception as exc:
        failures.append(f"runtime WebSocket/RPC/provider/browser path: {exc}")

    browser_health_code = dedent('''
        import json, urllib.request
        data = json.load(urllib.request.urlopen("http://127.0.0.1:9100/health", timeout=5))
        ok = data.get("status") == "ONLINE" and data.get("service") == "sarembok-browser" and data.get("engine") == "chromium"
        print(json.dumps({"ok": ok, "health": data}, sort_keys=True))
        raise SystemExit(0 if ok else 1)
    ''')
    try:
        data = json.loads(run_in_container("sarembok-browser", browser_health_code))
        print("[PASS] browser worker 9100:", json.dumps(data["health"], sort_keys=True))
    except Exception as exc:
        failures.append(f"browser worker 9100: {exc}")

    playwright_code = dedent('''
        from playwright.sync_api import sync_playwright
        import json

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda exc: errors.append("pageerror: " + str(exc)))
            page.on("console", lambda msg: errors.append("console: " + msg.text) if msg.type == "error" else None)
            page.goto("https://sarembok.com/", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)

            page.on("pageerror", lambda exc: errors.append("pageerror: " + str(exc)))
            page.on("console", lambda msg: errors.append("console: " + msg.text) if msg.type == "error" else None)

            health = page.evaluate("window.__srbkRuntimeUiHealth || null")
            if not page.locator("#global-input-field").is_visible():
                raise RuntimeError("canonical global composer is not visible")
            if not page.locator("#global-send-btn").is_visible():
                raise RuntimeError("canonical global send button is not visible")
            if not page.evaluate("typeof window.renderStructuredResponse === 'function'"):
                raise RuntimeError("structured response renderer is not installed")
            if not health:
                raise RuntimeError("runtime UI health snapshot missing")
            if not health.get("rpcRecovery"):
                raise RuntimeError("RPC recovery wrapper not installed")
            if not health.get("navigation"):
                raise RuntimeError("navigation health failed")
            if not health.get("markdownRenderer"):
                raise RuntimeError("Markdown renderer health failed")

            global_input = page.locator("#global-input-field")
            global_send = page.locator("#global-send-btn")
            if global_input.count() != 1 or global_send.count() != 1:
                raise RuntimeError("global chat composer not found")
            if not global_input.is_visible() or not global_send.is_visible():
                raise RuntimeError("global chat composer is not visible")

            theme = page.locator("#srbk-theme-toggle")
            if theme.count() != 1:
                raise RuntimeError(f"expected one theme control, found {theme.count()}")
            before = page.locator("html").get_attribute("data-theme")
            theme.click()
            page.wait_for_timeout(150)
            after = page.locator("html").get_attribute("data-theme")
            theme.click()
            page.wait_for_timeout(150)
            restored = page.locator("html").get_attribute("data-theme")
            if before == after or before != restored:
                raise RuntimeError(f"theme toggle failed: {before} -> {after} -> {restored}")

            nav_ids = page.locator(".dock-btn").evaluate_all("els => els.map(e => e.id.replace(/^dock-btn-/, ''))")
            if not nav_ids:
                raise RuntimeError("no navigation buttons found")
            for tab in nav_ids:
                page.locator(f"#dock-btn-{tab}").click()
                page.wait_for_timeout(150)
                if not page.locator(f"#view-{tab}.active").count():
                    raise RuntimeError(f"tab did not activate: {tab}")

            page.locator("#dock-btn-dialogue").click()
            page.wait_for_timeout(400)
            dialogue = page.locator("#view-dialogue")
            if dialogue.count() != 1 or not dialogue.is_visible():
                raise RuntimeError("Dialogue view is not visible after navigation")

            before_count = page.locator("#dialogue-history .srbk-bubble.assistant").count()
            global_input.fill("Use this exact phrase in your response: **SAREMBOK_EXECUTE_SMOKE**")
            global_send.click()

            page.wait_for_function(
                "(n) => document.querySelectorAll('#dialogue-history .srbk-bubble.assistant').length > n",
                arg=before_count,
                timeout=45000,
            )
            page.wait_for_timeout(800)

            latest = page.locator("#dialogue-history .srbk-bubble.assistant").last
            text_value = latest.inner_text()
            html_value = latest.locator(".srbk-content").inner_html()
            if "SAREMBOK_EXECUTE_SMOKE" not in text_value:
                raise RuntimeError("global Execute returned without requested response marker")
            if "\\\\*\\\\*" in html_value:
                raise RuntimeError("renderer still exposes escaped Markdown delimiters")

            rendered = page.evaluate("window.md(" + json.dumps("**MARKDOWN_SMOKE**\\n\\n- one\\n- two") + ")")
            if "<strong>MARKDOWN_SMOKE</strong>" not in rendered or "<li" not in rendered:
                raise RuntimeError("Markdown renderer deterministic test failed")

            print(json.dumps({
                "health": health,
                "theme": [before, after, restored],
                "tabs": nav_ids,
                "global_composer_visible": True,
                "dialogue_visible": True,
                "execute_response_contains_marker": True,
                "execute_html_has_strong": "<strong>" in html_value,
                "markdown_smoke": True,
                "page_errors": errors,
            }, sort_keys=True))
            browser.close()
    ''')
    try:
        out = run_in_container("sarembok-browser", playwright_code)
        print("[PASS] Playwright UI Execute + navigation + theme + Markdown:", out)
    except Exception as exc:
        failures.append(f"Playwright UI Execute/navigation/theme/Markdown: {exc}")

    print("===== RESULT =====")
    if failures:
        for failure in failures:
            print("[FAIL]", failure)
        return 1
    print("[PASS] ALL PRODUCTION UI SMOKE CHECKS V3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
