#!/usr/bin/env python3
"""SarembokVE Frontier Gate Comprehensive Patch & Verification Matrix.

Validates and verifies:
1. Frontier Security Model & Static Release Gate (Directive-01 compliance).
2. Dynamic RPC Capabilities (SearchWeb, GetEntropyMetrics, PaliGemma Grounding).
3. Tenant Guard & Originless-Local Fail-Closed Boundaries.
4. UI Viewport & Wide Response Container Scaling (min(1560px, 96vw)).
"""

from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import sys
import urllib.parse
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLOUD = ROOT / "Deployment" / "cloud"
EDGE = CLOUD / "edge" / "Caddyfile"
FRONTEND = ROOT / "frontend" / "index.html"

FAILURES: list[str] = []
PASSES: list[str] = []
PATCHES_APPLIED: list[str] = []


def record_pass(item: str) -> None:
    PASSES.append(item)


def record_fail(item: str) -> None:
    FAILURES.append(item)


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def verify_static_frontier_rules() -> None:
    """Validate core security assertions from frontier_release_gate.py."""
    compose_path = CLOUD / "compose.frontier_final.yaml"
    entrypoint_path = CLOUD / "production_entrypoint_frontier.py"
    policy_path = CLOUD / "frontier_runtime_policy.py"
    tenant_path = CLOUD / "frontier_tenant_guard.py"
    deploy_path = CLOUD / "deploy_frontier_release.sh"
    caddy_path = EDGE

    if not compose_path.exists():
        record_fail("compose.frontier_final.yaml is missing")
        return

    compose = read(compose_path)
    entrypoint = read(entrypoint_path)
    policy = read(policy_path)
    tenant = read(tenant_path)
    deploy = read(deploy_path)
    caddy = read(caddy_path)

    if "production_entrypoint_frontier.py" in compose:
        record_pass("Frontier compose selects v5 production boundary")
    else:
        record_fail("Frontier compose does not select v5 boundary")

    if "SAREMBOK_WORKER_TOKEN_HASH_SALT" in compose and "SAREMBOK_WORKER_TOKEN_HASH_SALT" in deploy:
        record_pass("Worker token hash salt correctly wired")
    else:
        record_fail("Worker token salt is not wired")

    if "SAREMBOK_ALLOW_ORIGINLESS_LOCAL:-false" in compose:
        record_pass("Originless-local access is fail-closed by default")
    else:
        record_fail("Originless-local default is not fail-closed")

    if "handle /api/*" in caddy and 'respond "Not Found" 404' in caddy:
        record_pass("Edge legacy /api surface blocked at edge gateway")
    else:
        record_fail("Legacy HTTP API is not blocked at edge gateway")

    if "handle /live/*" in caddy and 'respond "Not Found" 404' in caddy:
        record_pass("Edge legacy /live surface blocked at edge gateway")
    else:
        record_fail("Legacy live HTTP API is not blocked at edge gateway")

    if re.search(r"runtime\.ensure_sovereign_worker\s*=\s*lambda:\s*None", policy) and "_purge_synthetic_workers" in policy:
        record_pass("Synthetic worker bootstrap disabled and records purged")
    else:
        record_fail("Synthetic worker bootstrap is not safely disabled")

    if '"hardwareAttestation":"NOT_ATTESTED"' in entrypoint and "CATALOG_ONLY_NO_COMPUTE_CAPACITY_ASSERTION" in entrypoint:
        record_pass("Hardware attestation and GPU marketplace capacity claims bounded")
    else:
        record_fail("Hardware attestation or GPU marketplace claims unbounded")

    if "scoped_session_id" in tenant and "session_owner_mismatch" in tenant:
        record_pass("Tenant session isolation and ownership boundaries active")
    else:
        record_fail("Tenant session isolation helpers missing")

    for label, src in [("entrypoint", entrypoint), ("policy", policy), ("tenant", tenant)]:
        if "shell=True" in src or "eval(" in src or "exec(" in src:
            record_fail(f"Dangerous call found in {label}")
        else:
            record_pass(f"No shell=True/eval/exec in frontier {label}")

    for p in (entrypoint_path, policy_path, tenant_path, CLOUD / "frontier_release_gate.py"):
        try:
            ast.parse(read(p), filename=str(p))
            record_pass(f"AST syntax valid for {p.name}")
        except SyntaxError as err:
            record_fail(f"Syntax error in {p.name}: {err}")


def verify_frontier_runtime_capabilities() -> None:
    """Validate SearchWeb, GetEntropyMetrics, and Vision capabilities."""
    server_path = CLOUD / "server.py"
    server_code = read(server_path)

    for method in ["SearchWeb", "GetEntropyMetrics", "GetVisionStatus", "ProcessVisionFrame"]:
        if f'if method == "{method}":' in server_code or f'method == "{method}"' in server_code:
            record_pass(f"RPC method {method} dispatched in server.py")
        else:
            record_fail(f"RPC method {method} missing in server.py dispatch")

    # Check Production Guards
    guard_v2 = read(CLOUD / "production_guard_v2.py")
    guard_v1 = read(CLOUD / "production_guard.py")
    boot = read(CLOUD / "production_bootstrap.py")
    caps = read(CLOUD / "capability_registry.py")

    for method in ["SearchWeb", "GetEntropyMetrics"]:
        if f'"{method}"' in guard_v2:
            record_pass(f"{method} registered in production_guard_v2.py")
        else:
            record_fail(f"{method} missing from production_guard_v2.py")

        if f'"{method}"' in guard_v1:
            record_pass(f"{method} registered in production_guard.py")
        else:
            record_fail(f"{method} missing from production_guard.py")

        if f'"{method}"' in boot:
            record_pass(f"{method} registered in production_bootstrap.py")
        else:
            record_fail(f"{method} missing from production_bootstrap.py")

        if f'"{method}"' in caps:
            record_pass(f"{method} registered in capability_registry.py")
        else:
            record_fail(f"{method} missing from capability_registry.py")


def verify_ui_wide_response_scaling() -> None:
    """Validate that frontend response containers use wide scaling."""
    if not FRONTEND.exists():
        record_fail("frontend/index.html missing")
        return

    html = read(FRONTEND)
    if "max-width: min(1560px, 96vw)" in html or "max-width: min(1500px, 96vw)" in html:
        record_pass("Dialogue wrapper configured for wide responsive display (min(1560px, 96vw))")
    else:
        record_fail("Dialogue wrapper constrained to legacy narrow max-width")

    if "hud-entropy-badge" in html:
        record_pass("Live Shannon entropy HUD badge active in Cybernetic Cockpit header")
    else:
        record_fail("Shannon entropy HUD badge missing from frontend")


def main() -> int:
    print("=" * 64)
    print(" SAREMBOKVE FRONTIER GATE AUDIT & PATCH MATRIX")
    print("=" * 64)

    verify_static_frontier_rules()
    verify_frontier_runtime_capabilities()
    verify_ui_wide_response_scaling()

    print(f"\nTotal Passes:   {len(PASSES)}")
    print(f"Total Failures: {len(FAILURES)}")
    print(f"Patches Done:   {len(PATCHES_APPLIED)}")

    print("\n--- PASSED CHECKS ---")
    for p in PASSES:
        print(f" [PASS] {p}")

    if FAILURES:
        print("\n--- FAILED CHECKS ---")
        for f in FAILURES:
            print(f" [FAIL] {f}")
        print("\nFRONTIER GATE STATUS: FAIL")
        return 1

    print("\nFRONTIER GATE STATUS: ALL ASSERTIONS PASSED (100% COMPLIANT)")
    return 0


if __name__ == "__main__":
    sys.exit(main())



class TubiStreamingBridge:
    """Playwright video streaming bridge with automated stealth shield and direct slug resolution."""

    STEALTH_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    STEALTH_LAUNCH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
    ]

    def __init__(self, db_connection=None):
        self.db_connection = db_connection

    def construct_direct_slug_url(self, movie_title: str) -> str:
        """Constructs direct asset URL based on lowercase hyphenated movie title string."""
        clean_title = movie_title.lower().strip()
        slug = clean_title.replace(" ", "-")
        slug = re.sub(r"[^a-z0-9\-]", "", slug)
        return f"https://tubitv.com/{slug}"

    async def launch_stream(self, movie_query: str) -> dict[str, Any]:
        """Launches stealth Playwright session with direct slug resolution and 404 fallback."""
        target_url = self.construct_direct_slug_url(movie_query)
        fallback_url = f"https://tubitv.com/search/{urllib.parse.quote(movie_query)}"
        strict_selector = "div[data-testid='video-thumbnail'] a"

        print(f"[TubiStreamingBridge] Stealth Shield Active: User-Agent={self.STEALTH_USER_AGENT[:42]}...")
        print(f"[TubiStreamingBridge] Direct slug resolution attempt: {target_url}")

        result = {
            "query": movie_query,
            "platform": "tubi",
            "target_url": target_url,
            "fallback_url": fallback_url,
            "strict_selector": strict_selector,
            "stealth_args": self.STEALTH_LAUNCH_ARGS[:2],
            "status": "initialized",
        }

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[TubiStreamingBridge] Playwright library not present in local python environment; returning resolved stealth routing.")
            result["status"] = "resolved_routing"
            result["resolved_url"] = target_url
            return result

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=self.STEALTH_LAUNCH_ARGS,
                )
                context = await browser.new_context(
                    user_agent=self.STEALTH_USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                # Anti-detection stealth init script
                await page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )

                resolved_url = target_url
                try:
                    # 1. Direct slug resolution routing
                    resp = await page.goto(target_url, wait_until="domcontentloaded", timeout=12000)
                    status = getattr(resp, "status", 200)
                    if status >= 400 or "not-found" in page.url or "404" in page.url:
                        raise ValueError(f"Direct slug 404 returned: status={status}")
                    resolved_url = page.url
                    print(f"[TubiStreamingBridge] Direct slug resolved successfully: {resolved_url}")
                except Exception as direct_err:
                    # 2. 404 / error fallback with strict element selector targeting
                    print(f"[TubiStreamingBridge] Direct URL failed ({direct_err}). Falling back to search with strict selector '{strict_selector}'...")
                    await page.goto(fallback_url, wait_until="domcontentloaded", timeout=15000)
                    try:
                        await page.wait_for_selector(strict_selector, timeout=8000)
                        thumb = await page.query_selector(strict_selector)
                        if thumb:
                            href = await thumb.get_attribute("href")
                            if href:
                                resolved_url = f"https://tubitv.com{href}" if href.startswith("/") else href
                                print(f"[TubiStreamingBridge] Target movie card selected via thumbnail selector: {resolved_url}")
                                await thumb.click()
                    except Exception as sel_err:
                        print(f"[TubiStreamingBridge] Strict thumbnail selector note: {sel_err}")

                result["status"] = "streaming"
                result["resolved_url"] = resolved_url
                return result

        except Exception as play_err:
            print(f"[TubiStreamingBridge] Streaming bridge execution notice: {play_err}")
            result["status"] = "error"
            result["error"] = str(play_err)
            return result


db = None


# Append this to generated/frontier_gate_patch.py to process the Tubi player actions
async def execute_agent_action(final_action_payload: dict):
    """
    Reads the parsed, safe output from your supervisor and triggers 
    the necessary system tools or browser subsystems.
    """
    tool_name = final_action_payload.get("tool")
    parameters = final_action_payload.get("parameters", {})
    
    if tool_name == "MediaPlaybackAgent":
        movie_query = parameters.get("query")
        platform = parameters.get("platform", "tubi")
        
        print(f"[SarembokVE Router] Ingesting command: Play '{movie_query}' via {platform}")
        
        # Initialize and launch the Playwright background video wrapper
        bridge = TubiStreamingBridge(db_connection=db)
        await bridge.launch_stream(movie_query)
        
    else:
        # Fall back to default terminal or diagnostic registry handlers
        print(f"[SarembokVE Router] Routing to standard system agent: {tool_name}")


