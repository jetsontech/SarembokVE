"""Production entrypoint security/truth-boundary gates."""

from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "runtime_entrypoint_v3.py"
DOCKERFILE = ROOT / "Dockerfile"
ENTRYPOINT_SOURCE = ENTRYPOINT.read_text(encoding="utf-8")
DOCKER_SOURCE = DOCKERFILE.read_text(encoding="utf-8")


class RuntimeSecurityContractTests(unittest.TestCase):
    def test_production_container_uses_hardened_entrypoint(self) -> None:
        self.assertIn('CMD ["python", "/app/runtime_entrypoint_v3.py"]', DOCKER_SOURCE)
        self.assertNotIn('CMD ["python", "/app/server.py"]', DOCKER_SOURCE)
        self.assertNotIn('CMD ["python", "/app/knowledge_rpc_server.py"]', DOCKER_SOURCE)

    def test_admin_secret_fails_closed(self) -> None:
        self.assertIn("SAREMBOK_ADMIN_PASSCODE", ENTRYPOINT_SOURCE)
        self.assertIn("SAREMBOK_AUTH_TOKEN", ENTRYPOINT_SOURCE)
        self.assertIn("refusing to start with a default credential", ENTRYPOINT_SOURCE)
        self.assertRegex(ENTRYPOINT_SOURCE, r"len\(secret\) < 16")
        self.assertNotIn('"sarembok2026"', ENTRYPOINT_SOURCE)
        self.assertNotIn('"joc"', ENTRYPOINT_SOURCE)

    def test_browser_sessions_do_not_expose_sensitive_operations(self) -> None:
        sensitive = {
            "BrowserNavigate", "BrowserScreenshot", "BrowserRender",
            "AdminExecuteDirective", "VerifyAdminPasscode", "AuthenticateSocialUser",
            "RegisterWorker", "Heartbeat", "ClaimTask", "CompleteTask", "FailTask",
            "ScheduleCompute", "CreateTask", "ExecuteSandboxCode",
            "RentGpuNode", "SaveUserChatSession", "DeleteUserChatSession",
        }
        allowlist = re.search(
            r"cloud\.BROWSER_ALLOWED_METHODS\s*=\s*\{(?P<body>.*?)\n\}",
            ENTRYPOINT_SOURCE, re.DOTALL,
        )
        self.assertIsNotNone(allowlist)
        body = allowlist.group("body")
        for method in sensitive:
            self.assertNotIn(f'"{method}"', body)

    def test_execute_compute_is_public_but_truth_bound(self) -> None:
        allowlist = re.search(
            r"cloud\.BROWSER_ALLOWED_METHODS\s*=\s*\{(?P<body>.*?)\n\}",
            ENTRYPOINT_SOURCE, re.DOTALL,
        )
        self.assertIsNotNone(allowlist)
        self.assertIn('"ExecuteComputeTask"', allowlist.group("body"))
        self.assertIn('"status": "PENDING_WORKER"', ENTRYPOINT_SOURCE)
        self.assertNotIn('"status": "RUNNING"', re.search(
            r'if method == "ExecuteComputeTask":(?P<body>.*?)(?=\n\s*if method == "CreateDigitalHumanSession")',
            ENTRYPOINT_SOURCE, re.DOTALL,
        ).group("body"))

    def test_direct_browser_control_is_blocked_even_with_stronger_auth(self) -> None:
        self.assertIn('method in {"BrowserNavigate", "BrowserScreenshot", "BrowserRender"}', ENTRYPOINT_SOURCE)
        self.assertIn("browser_control_unavailable", ENTRYPOINT_SOURCE)

    def test_synthetic_worker_is_disabled_and_purged(self) -> None:
        self.assertIn("cloud.ensure_sovereign_worker = _no_synthetic_worker", ENTRYPOINT_SOURCE)
        self.assertIn("DELETE FROM workers WHERE worker_id='sarembok-edge-frontier-01'", ENTRYPOINT_SOURCE)
        self.assertNotIn("NVIDIA RTX 4090 Sovereign Tensor Core", ENTRYPOINT_SOURCE)

    def test_compute_never_claims_running_without_worker(self) -> None:
        block = re.search(
            r'if method == "ExecuteComputeTask":(?P<body>.*?)(?=\n\s*if method == "CreateDigitalHumanSession")',
            ENTRYPOINT_SOURCE, re.DOTALL,
        )
        self.assertIsNotNone(block)
        body = block.group("body")
        self.assertIn("PENDING_WORKER", body)
        self.assertNotIn('"status": "RUNNING"', body)
        self.assertNotIn("SOVEREIGN_WORKER_ID", body)

    def test_unsafe_in_process_sandbox_is_blocked(self) -> None:
        self.assertIn('method == "ExecuteSandboxCode"', ENTRYPOINT_SOURCE)
        self.assertIn("sandbox_execution_unavailable", ENTRYPOINT_SOURCE)

    def test_admin_shell_and_python_are_blocked(self) -> None:
        self.assertIn('method == "AdminExecuteDirective"', ENTRYPOINT_SOURCE)
        self.assertIn("admin_execution_unavailable", ENTRYPOINT_SOURCE)

    def test_unverified_social_identity_is_blocked(self) -> None:
        self.assertIn('method == "AuthenticateSocialUser"', ENTRYPOINT_SOURCE)
        self.assertIn("social_auth_unavailable", ENTRYPOINT_SOURCE)

    def test_unowned_chat_sessions_are_blocked(self) -> None:
        self.assertIn("user_session_authentication_required", ENTRYPOINT_SOURCE)
        allowlist = ENTRYPOINT_SOURCE.split("cloud.BROWSER_ALLOWED_METHODS", 1)[1].split("\n}\n", 1)[0]
        for method in ("ListUserChatSessions", "SaveUserChatSession", "DeleteUserChatSession"):
            self.assertNotIn(f'"{method}"', allowlist)

    def test_image_generation_does_not_claim_a_local_worker(self) -> None:
        self.assertIn('method == "GenerateImage"', ENTRYPOINT_SOURCE)
        self.assertIn('result["workerId"] = None', ENTRYPOINT_SOURCE)
        self.assertIn('result["executionMode"] = "provider_routed"', ENTRYPOINT_SOURCE)

    def test_visual_tier_three_is_not_reported_as_verified_online(self) -> None:
        self.assertIn('tier3["status"] = "AVAILABLE_IF_REACHABLE"', ENTRYPOINT_SOURCE)


if __name__ == "__main__":
    unittest.main()
