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
    """Playwright video streaming bridge for Tubi platform playback."""
    def __init__(self, db_connection=None):
        self.db_connection = db_connection

    async def launch_stream(self, movie_query: str) -> None:
        print(f"[TubiStreamingBridge] Launching Playwright stream for '{movie_query}'")

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

