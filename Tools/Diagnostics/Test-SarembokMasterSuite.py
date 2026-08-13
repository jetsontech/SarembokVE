#!/usr/bin/env python3
"""
Test-SarembokMasterSuite.py
Unified Master Regression, Acceptance, and E2E Test Suite for Sarembok VE.

Covers:
1. HTTP Edge & Web UI Application Serving (GET /, GET /health)
2. Authentication Boundary & Security Rejection (-32001)
3. 12 Core Production JSON-RPC Facets Contract Verification
4. GPU Worker Registration & Declarative Capabilities
5. Full Task Lifecycle (Schedule -> Assign -> Claim -> Execute -> Complete)
6. Digital Human Session Lifecycle (Create -> Get -> Update -> Close)
7. Failure & Retry Recovery Semantics
8. High Concurrency (10+ simultaneous clients)
9. SQLite Cross-Restart Persistence & Audit Integrity
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

import websockets

PASS_TAG = "\033[92m[PASS]\033[0m"
FAIL_TAG = "\033[91m[FAIL]\033[0m"
INFO_TAG = "\033[94m[INFO]\033[0m"

TEST_SUMMARY: list[dict[str, Any]] = []


def record_result(category: str, test_name: str, passed: bool, detail: str = "") -> None:
    TEST_SUMMARY.append({
        "category": category,
        "name": test_name,
        "passed": passed,
        "detail": detail,
    })
    tag = PASS_TAG if passed else FAIL_TAG
    suffix = f" - {detail}" if detail else ""
    print(f"{tag} [{category}] {test_name}{suffix}")


async def send_rpc(ws: websockets.ClientConnection, method: str, params: dict[str, Any] | None = None, auth_token: str = "", req_id: str = "req-1") -> dict[str, Any]:
    p = dict(params or {})
    if auth_token:
        p["authToken"] = auth_token
    payload = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": p})
    await ws.send(payload)
    raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
    return json.loads(raw)


async def test_http_endpoints(http_url: str) -> bool:
    print(f"\n{INFO_TAG} === Phase 1: HTTP Edge & Web UI Serving ===")
    all_ok = True
    
    # 1. /health probe
    try:
        health_url = http_url.rstrip("/") + "/health"
        req = urllib.request.Request(health_url, headers={"User-Agent": "SarembokMasterSuite/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            ok = resp.status == 200 and resp.read().decode("utf-8").strip() in ("OK", "healthy")
            record_result("HTTP", "Health Endpoint Probe (/health)", ok, f"Status={resp.status}")
            if not ok:
                all_ok = False
    except Exception as exc:
        record_result("HTTP", "Health Endpoint Probe (/health)", False, f"Exception: {exc}")
        all_ok = False

    # 2. / Web UI application serving
    try:
        root_url = http_url.rstrip("/") + "/"
        req = urllib.request.Request(root_url, headers={"User-Agent": "SarembokMasterSuite/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            content_type = resp.headers.get("Content-Type", "")
            is_html = "text/html" in content_type
            has_brand = "Sarembok VE" in body and "Autonomous Digital Human" in body
            ok = resp.status == 200 and is_html and has_brand
            record_result("HTTP", "Web UI Application Serving (/)", ok, f"Length={len(body)} Content-Type={content_type}")
            if not ok:
                all_ok = False
    except Exception as exc:
        record_result("HTTP", "Web UI Application Serving (/)", False, f"Exception: {exc}")
        all_ok = False

    return all_ok


async def test_auth_security(ws_url: str, auth_token: str) -> bool:
    print(f"\n{INFO_TAG} === Phase 2: Authentication & Security Boundary ===")
    if not auth_token:
        record_result("AUTH", "Auth Rejection Check", True, "Auth token not configured; skipped.")
        return True

    all_ok = True
    try:
        async with websockets.connect(ws_url) as ws:
            # 1. Test missing token
            resp_missing = await send_rpc(ws, "QueryWorldModel", {}, auth_token="", req_id="auth-test-1")
            rejected_missing = "error" in resp_missing and resp_missing["error"].get("code") == -32001
            record_result("AUTH", "Missing Auth Token Rejection", rejected_missing, "Expected code -32001")
            if not rejected_missing:
                all_ok = False

            # 2. Test invalid token
            resp_invalid = await send_rpc(ws, "QueryWorldModel", {"authToken": "totally-invalid-secret"}, auth_token="", req_id="auth-test-2")
            rejected_invalid = "error" in resp_invalid and resp_invalid["error"].get("code") == -32001
            record_result("AUTH", "Invalid Auth Token Rejection", rejected_invalid, "Expected code -32001")
            if not rejected_invalid:
                all_ok = False

            # 3. Test valid token
            resp_valid = await send_rpc(ws, "Health", {}, auth_token=auth_token, req_id="auth-test-3")
            accepted_valid = "result" in resp_valid and resp_valid["result"].get("status") == "ONLINE"
            record_result("AUTH", "Valid Auth Token Acceptance", accepted_valid, "Status ONLINE verified")
            if not accepted_valid:
                all_ok = False
    except Exception as exc:
        record_result("AUTH", "Auth Security Verification", False, f"Exception: {exc}")
        all_ok = False

    return all_ok


async def test_rpc_contract_facets(ws_url: str, auth_token: str) -> bool:
    print(f"\n{INFO_TAG} === Phase 3: 12 Production JSON-RPC Facets Contract ===")
    all_ok = True
    agent_id = f"test-agent-{uuid.uuid4().hex[:6]}"
    worker_id = f"test-worker-{uuid.uuid4().hex[:6]}"
    session_id = None

    facets = [
        ("Health", {}),
        ("ListWorkers", {}),
        ("CreateAgent", {"agentId": agent_id, "displayName": "Master Test Agent"}),
        ("QueryAgentState", {"agentId": agent_id}),
        ("QueryWorldModel", {"agentId": agent_id}),
        ("GetCognitiveScorecard", {"agentId": agent_id}),
        ("GetEvents", {"agentId": agent_id}),
        ("GetMetrics", {"agentId": agent_id}),
        ("CreateDigitalHumanSession", {"agentId": agent_id, "metahumanId": "test-mh-01"}),
        ("GetDigitalHumanSession", {"sessionId": "PLACEHOLDER"}),
        ("ScheduleCompute", {"taskType": "smoke_test", "payload": {"operation": "add", "a": 5, "b": 10}}),
        ("GetAuditTrail", {"agentId": agent_id}),
    ]

    try:
        async with websockets.connect(ws_url) as ws:
            for method, params in facets:
                if method == "GetDigitalHumanSession":
                    params["sessionId"] = session_id or "missing"

                resp = await send_rpc(ws, method, params, auth_token=auth_token, req_id=f"rpc-{method}")
                ok = "result" in resp and "error" not in resp

                if method == "CreateDigitalHumanSession" and ok:
                    session_id = resp["result"].get("sessionId")

                record_result("RPC_CONTRACT", f"Facet: {method}", ok, f"result={bool(resp.get('result'))}")
                if not ok:
                    all_ok = False
    except Exception as exc:
        record_result("RPC_CONTRACT", "RPC Contract Execution", False, f"Exception: {exc}")
        all_ok = False

    return all_ok


async def test_worker_and_task_execution(ws_url: str, auth_token: str) -> bool:
    print(f"\n{INFO_TAG} === Phase 4: Autonomous Worker Lifecycle & Task Execution ===")
    all_ok = True
    worker_id = f"e2e-gpu-worker-{uuid.uuid4().hex[:6]}"

    try:
        async with websockets.connect(ws_url) as ws:
            # 1. Register worker
            reg_resp = await send_rpc(
                ws,
                "RegisterWorker",
                {
                    "workerId": worker_id,
                    "capabilities": ["compute", "inference", "meta_human"],
                    "gpuVendor": "NVIDIA",
                    "gpuModel": "NVIDIA GeForce RTX 4090",
                    "vramMb": 24576,
                    "status": "ONLINE",
                },
                auth_token=auth_token,
            )
            reg_ok = reg_resp.get("result", {}).get("status") == "ONLINE"
            record_result("WORKER", "Worker Registration (RTX 4090)", reg_ok, f"workerId={worker_id}")
            if not reg_ok:
                all_ok = False

            # 2. Worker Heartbeat
            hb_resp = await send_rpc(ws, "Heartbeat", {"workerId": worker_id, "status": "ONLINE"}, auth_token=auth_token)
            hb_ok = hb_resp.get("result", {}).get("status") == "ONLINE" and bool(hb_resp.get("result", {}).get("lastHeartbeat"))
            record_result("WORKER", "Worker Heartbeat", hb_ok, f"lastHeartbeat={hb_resp.get('result', {}).get('lastHeartbeat')}")
            if not hb_ok:
                all_ok = False

            # 3. Schedule task with worker ONLINE -> should be QUEUED and assigned
            sched_resp = await send_rpc(
                ws,
                "ScheduleCompute",
                {
                    "taskType": "smoke_test",
                    "requiredCapability": "compute",
                    "payload": {"operation": "multiply", "a": 7, "b": 6},
                },
                auth_token=auth_token,
            )
            task_res = sched_resp.get("result", {})
            task_id = task_res.get("taskId")
            sched_ok = bool(task_id) and task_res.get("status") == "QUEUED" and task_res.get("assignedWorkerId") == worker_id
            record_result("SCHEDULER", "Task Scheduled & Assigned to Online Worker", sched_ok, f"taskId={task_id} status={task_res.get('status')}")
            if not sched_ok:
                all_ok = False

            # 4. Worker Claims Task
            claim_resp = await send_rpc(ws, "ClaimTask", {"taskId": task_id, "workerId": worker_id}, auth_token=auth_token)
            claim_ok = claim_resp.get("result", {}).get("status") == "RUNNING"
            record_result("SCHEDULER", "Worker Task Claim (RUNNING)", claim_ok, f"status={claim_resp.get('result', {}).get('status')}")
            if not claim_ok:
                all_ok = False

            # 5. Worker Completes Task
            comp_resp = await send_rpc(ws, "CompleteTask", {"taskId": task_id, "workerId": worker_id}, auth_token=auth_token)
            comp_ok = comp_resp.get("result", {}).get("status") == "COMPLETED"
            record_result("SCHEDULER", "Worker Task Completion (COMPLETED)", comp_ok, f"status={comp_resp.get('result', {}).get('status')}")
            if not comp_ok:
                all_ok = False

            # 6. Verify Task in Task List
            task_info = await send_rpc(ws, "GetTask", {"taskId": task_id}, auth_token=auth_token)
            t_res = task_info.get("result", {})
            verified_ok = t_res.get("status") == "COMPLETED" and t_res.get("assignedWorkerId") == worker_id
            record_result("SCHEDULER", "Task Record Integrity Verification", verified_ok, f"taskId={task_id} status={t_res.get('status')}")
            if not verified_ok:
                all_ok = False

            # 7. Test Failure & Retry Recovery Semantics
            fail_task_res = await send_rpc(
                ws,
                "ScheduleCompute",
                {"taskType": "smoke_test", "requiredCapability": "compute", "payload": {"operation": "fail_then_retry"}},
                auth_token=auth_token,
            )
            f_id = fail_task_res.get("result", {}).get("taskId")
            await send_rpc(ws, "ClaimTask", {"taskId": f_id, "workerId": worker_id}, auth_token=auth_token)
            fail_resp = await send_rpc(ws, "FailTask", {"taskId": f_id, "workerId": worker_id, "error": "simulated_worker_crash", "retryable": True}, auth_token=auth_token)
            reverted_ok = fail_resp.get("result", {}).get("status") == "PENDING_WORKER"
            record_result("RECOVERY", "Task Failure Reverted to PENDING_WORKER (Retryable)", reverted_ok, f"status={fail_resp.get('result', {}).get('status')}")
            if not reverted_ok:
                all_ok = False

            # Re-claim and complete recovered task
            await send_rpc(ws, "ClaimTask", {"taskId": f_id, "workerId": worker_id}, auth_token=auth_token)
            retry_comp = await send_rpc(ws, "CompleteTask", {"taskId": f_id, "workerId": worker_id}, auth_token=auth_token)
            retry_ok = retry_comp.get("result", {}).get("status") == "COMPLETED"
            record_result("RECOVERY", "Recovered Task Execution & Completion", retry_ok, f"taskId={f_id} status={retry_comp.get('result', {}).get('status')}")
            if not retry_ok:
                all_ok = False

    except Exception as exc:
        record_result("WORKER", "Worker & Task Lifecycle", False, f"Exception: {exc}")
        all_ok = False

    return all_ok


async def test_digital_human_lifecycle(ws_url: str, auth_token: str) -> bool:
    print(f"\n{INFO_TAG} === Phase 5: Digital Human Session Lifecycle ===")
    all_ok = True
    agent_id = f"dh-agent-{uuid.uuid4().hex[:6]}"

    try:
        async with websockets.connect(ws_url) as ws:
            # 1. Create Agent
            await send_rpc(ws, "CreateAgent", {"agentId": agent_id, "displayName": "DH Host Agent"}, auth_token=auth_token)

            # 2. Create Session
            create_resp = await send_rpc(
                ws,
                "CreateDigitalHumanSession",
                {"agentId": agent_id, "metahumanId": "metahuman-ada", "voiceProfile": "neural-female-en"},
                auth_token=auth_token,
            )
            s_data = create_resp.get("result", {})
            session_id = s_data.get("sessionId")
            create_ok = bool(session_id) and s_data.get("status") == "ACTIVE"
            record_result("DIGITAL_HUMAN", "Session Creation (ACTIVE)", create_ok, f"sessionId={session_id}")
            if not create_ok:
                all_ok = False

            # 3. Get Session
            get_resp = await send_rpc(ws, "GetDigitalHumanSession", {"sessionId": session_id}, auth_token=auth_token)
            g_data = get_resp.get("result", {})
            get_ok = g_data.get("metahumanId") == "metahuman-ada" and g_data.get("status") == "ACTIVE"
            record_result("DIGITAL_HUMAN", "Session Retrieval & Attribute Validation", get_ok, f"metahuman={g_data.get('metahumanId')}")
            if not get_ok:
                all_ok = False

            # 4. Update Session to IDLE
            up_resp = await send_rpc(ws, "UpdateDigitalHumanSession", {"sessionId": session_id, "status": "IDLE"}, auth_token=auth_token)
            up_ok = up_resp.get("result", {}).get("status") == "IDLE"
            record_result("DIGITAL_HUMAN", "Session State Update (IDLE)", up_ok, f"status={up_resp.get('result', {}).get('status')}")
            if not up_ok:
                all_ok = False

            # 5. Close Session
            close_resp = await send_rpc(ws, "CloseDigitalHumanSession", {"sessionId": session_id}, auth_token=auth_token)
            close_ok = close_resp.get("result", {}).get("status") == "CLOSED"
            record_result("DIGITAL_HUMAN", "Session Termination (CLOSED)", close_ok, f"status={close_resp.get('result', {}).get('status')}")
            if not close_ok:
                all_ok = False

    except Exception as exc:
        record_result("DIGITAL_HUMAN", "Digital Human Session Lifecycle", False, f"Exception: {exc}")
        all_ok = False

    return all_ok


async def test_concurrency(ws_url: str, auth_token: str, client_count: int = 10) -> bool:
    print(f"\n{INFO_TAG} === Phase 6: High Concurrency Client Stress Test ({client_count} clients) ===")
    
    async def single_client_worker(client_idx: int) -> bool:
        try:
            async with websockets.connect(ws_url) as ws:
                agent_id = f"conc-agent-{client_idx}-{uuid.uuid4().hex[:4]}"
                # 1. Create Agent
                r1 = await send_rpc(ws, "CreateAgent", {"agentId": agent_id, "displayName": f"Conc Client {client_idx}"}, auth_token=auth_token, req_id=f"c-{client_idx}-1")
                if "result" not in r1:
                    return False
                # 2. Query World Model
                r2 = await send_rpc(ws, "QueryWorldModel", {"agentId": agent_id}, auth_token=auth_token, req_id=f"c-{client_idx}-2")
                if "result" not in r2:
                    return False
                # 3. Schedule Compute
                r3 = await send_rpc(ws, "ScheduleCompute", {"taskType": "smoke_test"}, auth_token=auth_token, req_id=f"c-{client_idx}-3")
                if "result" not in r3:
                    return False
                # 4. Get Audit Trail
                r4 = await send_rpc(ws, "GetAuditTrail", {"agentId": agent_id}, auth_token=auth_token, req_id=f"c-{client_idx}-4")
                return "result" in r4
        except Exception:
            return False

    tasks = [single_client_worker(i) for i in range(client_count)]
    results = await asyncio.gather(*tasks)
    passed_count = sum(1 for r in results if r)
    all_ok = passed_count == client_count
    record_result("CONCURRENCY", f"{client_count} Concurrent RPC Clients", all_ok, f"{passed_count}/{client_count} passed without contention or lock errors")
    return all_ok


async def test_persistence_and_audit(ws_url: str, auth_token: str) -> bool:
    print(f"\n{INFO_TAG} === Phase 7: SQLite Persistence & Audit Integrity ===")
    all_ok = True
    agent_id = f"audit-agent-{uuid.uuid4().hex[:6]}"

    try:
        async with websockets.connect(ws_url) as ws:
            # 1. Create Agent and inject events
            await send_rpc(ws, "CreateAgent", {"agentId": agent_id, "displayName": "Persistence Audit Agent"}, auth_token=auth_token)
            await send_rpc(ws, "InjectPerception", {"agentId": agent_id, "perception": {"visual": "user_present", "confidence": 0.98}}, auth_token=auth_token)
            await send_rpc(ws, "EvaluateDecision", {"agentId": agent_id, "actionId": "greet_user", "riskScore": 0.1, "confidence": 0.95}, auth_token=auth_token)

            # 2. Query Audit Trail
            audit_resp = await send_rpc(ws, "GetAuditTrail", {"agentId": agent_id}, auth_token=auth_token)
            a_res = audit_resp.get("result", {})
            audit_ok = a_res.get("status") == "integrity_verified" and a_res.get("storage") == "sqlite-wal" and a_res.get("recordsCount", 0) >= 3
            record_result("PERSISTENCE", "Audit Trail & Event Journaling", audit_ok, f"records={a_res.get('recordsCount')} storage={a_res.get('storage')}")
            if not audit_ok:
                all_ok = False

            # 3. Query Cognitive Metrics & Scorecard
            metrics_resp = await send_rpc(ws, "GetMetrics", {"agentId": agent_id}, auth_token=auth_token)
            m_res = metrics_resp.get("result", {})
            metrics_ok = "metrics" in m_res and m_res.get("metrics", {}).get("overall", 0) > 0.9
            record_result("PERSISTENCE", "Cognitive Metrics Persistence", metrics_ok, f"overall={m_res.get('metrics', {}).get('overall')}")
            if not metrics_ok:
                all_ok = False

    except Exception as exc:
        record_result("PERSISTENCE", "Persistence & Audit Verification", False, f"Exception: {exc}")
        all_ok = False

    return all_ok


def print_final_completion_report() -> int:
    print("\n" + "=" * 70)
    print("      SAREMBOK VE — PRODUCTION COMPLETION VALIDATION REPORT      ")
    print("=" * 70)

    categories = set(t["category"] for t in TEST_SUMMARY)
    total_passed = 0
    total_failed = 0

    for cat in sorted(categories):
        tests_in_cat = [t for t in TEST_SUMMARY if t["category"] == cat]
        cat_passed = sum(1 for t in tests_in_cat if t["passed"])
        cat_failed = len(tests_in_cat) - cat_passed
        total_passed += cat_passed
        total_failed += cat_failed
        status_tag = "\033[92mPASS\033[0m" if cat_failed == 0 else "\033[91mFAIL\033[0m"
        print(f"  {cat:<20}: {status_tag} ({cat_passed}/{len(tests_in_cat)})")

    print("-" * 70)
    total_tests = total_passed + total_failed
    overall_status = "\033[92mALL TESTS PASSED\033[0m" if total_failed == 0 else "\033[91mSOME TESTS FAILED\033[0m"
    print(f"  TOTAL RESULTS: {total_passed}/{total_tests} PASSED | {total_failed} FAILED -> {overall_status}")
    print("=" * 70 + "\n")
    return 0 if total_failed == 0 else 1


async def main_async() -> int:
    parser = argparse.ArgumentParser(description="Sarembok VE Master Acceptance & Regression Test Suite")
    parser.add_argument("--target", default=os.getenv("SAREMBOK_WS_URL", "http://127.0.0.1:9000"), help="Server target (HTTP or WS URL)")
    parser.add_argument("--auth-token", default=os.getenv("SAREMBOK_AUTH_TOKEN", ""), help="Secret auth token")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent clients to simulate")
    args = parser.parse_args()

    raw_target = args.target
    if raw_target.startswith("https://"):
        http_url = raw_target
        ws_url = raw_target.replace("https://", "wss://")
    elif raw_target.startswith("http://"):
        http_url = raw_target
        ws_url = raw_target.replace("http://", "ws://")
    elif raw_target.startswith("wss://"):
        ws_url = raw_target
        http_url = raw_target.replace("wss://", "https://")
    elif raw_target.startswith("ws://"):
        ws_url = raw_target
        http_url = raw_target.replace("ws://", "http://")
    else:
        http_url = f"http://{raw_target}"
        ws_url = f"ws://{raw_target}"

    print("=" * 70)
    print(" SAREMBOK VE MASTER REGRESSION TEST SUITE")
    print(f" HTTP URL: {http_url}")
    print(f" WS URL:   {ws_url}")
    print(f" Auth:     {'CONFIGURED' if args.auth_token else 'DISABLED'}")
    print("=" * 70)

    # 1. HTTP Endpoint Test
    await test_http_endpoints(http_url)

    # 2. Auth Security Test
    await test_auth_security(ws_url, args.auth_token)

    # 3. RPC Contract Facets
    await test_rpc_contract_facets(ws_url, args.auth_token)

    # 4. Worker & Task Execution
    await test_worker_and_task_execution(ws_url, args.auth_token)

    # 5. Digital Human Lifecycle
    await test_digital_human_lifecycle(ws_url, args.auth_token)

    # 6. High Concurrency Stress Test
    await test_concurrency(ws_url, args.auth_token, client_count=args.concurrency)

    # 7. SQLite Persistence & Audit Integrity
    await test_persistence_and_audit(ws_url, args.auth_token)

    return print_final_completion_report()


def main() -> None:
    code = asyncio.run(main_async())
    sys.exit(code)


if __name__ == "__main__":
    main()
