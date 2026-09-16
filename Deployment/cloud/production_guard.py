"""Production control-plane guardrails for SarembokVE.

This module is deliberately independent from the legacy runtime dispatcher so
security policy can be enforced at the production WebSocket boundary without
changing the runtime contract.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

ROLES = {"PUBLIC", "USER", "WORKER", "OPERATOR", "ADMIN", "MASTER", "SYSTEM"}

READ_METHODS = {
    "GetRuntimeInfo", "GetProviderMetrics", "GetVisualEngineStatus",
    "ListWorkers", "ListTasks", "ListProjects", "GetCurrentUser",
    "GetFeedbackSummary", "ListMemories", "SearchMemories",
    "ListDigitalHumanSessions", "GetDigitalHumanSession",
    "ListMcpServers", "GetGpuMarketplace", "ListGpuRentals",
    "GetVisionStatus", "GetAdminStatus", "GetConversationHistory",
}

USER_METHODS = READ_METHODS | {
    "SarembokChat", "Chat", "SarembokDialogue",
    "BrowserNavigate", "BrowserScreenshot", "BrowserRender",
    "SubmitFeedback", "StoreMemory", "DeleteMemory",
    "CreateDigitalHumanSession", "CloseDigitalHumanSession",
    "SearchYouTube", "ResolveMediaStream", "ProcessVisionFrame",
    "SpatialVisualRecall", "GenerateImage",
    "SaveUserChatSession", "ListUserChatSessions", "DeleteUserChatSession",
}

WORKER_METHODS = {
    "RegisterWorker", "Heartbeat", "ClaimTask", "CompleteTask", "FailTask",
    "ExecuteComputeTask", "GetRuntimeInfo", "ListWorkers", "ListTasks",
}

OPERATOR_METHODS = {
    "CreateAgent", "CreateProject", "CreateTask", "ScheduleCompute",
    "InjectPerception", "EvaluateDecision", "CreateDelegation", "SendMessage",
    "RestoreState", "PruneWorkers", "ScaleWorkers", "RegisterMcpServer",
}

ADMIN_METHODS = OPERATOR_METHODS | {
    "AdminExecuteDirective", "RentGpuNode", "CancelActiveStream",
    "RegisterMcpServer", "DeleteMemory", "CloseDigitalHumanSession",
}

LOGIN_METHODS = {"AuthenticateMaster", "AuthenticateSocialUser", "VerifyAdminPasscode"}

# Legacy dispatcher methods that are not part of a browser-facing contract are
# denied unless an explicit system/admin identity is established.
DEFAULT_ROLE_REQUIREMENTS: dict[str, str] = {}
for _m in READ_METHODS:
    DEFAULT_ROLE_REQUIREMENTS[_m] = "USER"
for _m in USER_METHODS:
    DEFAULT_ROLE_REQUIREMENTS[_m] = "USER"
for _m in WORKER_METHODS:
    DEFAULT_ROLE_REQUIREMENTS[_m] = "WORKER"
for _m in OPERATOR_METHODS:
    DEFAULT_ROLE_REQUIREMENTS[_m] = "OPERATOR"
for _m in ADMIN_METHODS:
    DEFAULT_ROLE_REQUIREMENTS[_m] = "ADMIN"

SENSITIVE_METHODS = {
    "AdminExecuteDirective", "ScaleWorkers", "RentGpuNode", "RegisterMcpServer",
    "RegisterWorker", "ClaimTask", "CompleteTask", "FailTask", "ExecuteComputeTask",
    "DeleteMemory", "DeleteUserChatSession",
}

SECRET_KEY_PATTERNS = re.compile(
    r"(?i)(api[_-]?key|authorization|session[_-]?token|access[_-]?token|refresh[_-]?token|password|passcode|secret|worker[_-]?token)"
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "[REDACTED]" if SECRET_KEY_PATTERNS.search(str(k)) else scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, tuple):
        return tuple(scrub(v) for v in value)
    if isinstance(value, str):
        # Never emit common bearer-style credentials even when embedded in text.
        return re.sub(r"(?i)\b(sk-[A-Za-z0-9_-]{12,}|gsk_[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{20,}|sk-or-[A-Za-z0-9_-]{12,})\b", "[REDACTED]", value)
    return value


@dataclass
class Identity:
    role: str
    subject: str
    token_fingerprint: str = ""


class FixedWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = max(1, int(limit))
        self.window_seconds = max(1.0, float(window_seconds))
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            bucket = self._events.setdefault(key, deque())
            cutoff = now - self.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry = max(1, int(bucket[0] + self.window_seconds - now))
                return False, retry
            bucket.append(now)
            if len(self._events) > 10000:
                self._events = {k: v for k, v in self._events.items() if v}
            return True, 0


class IdempotencyCache:
    def __init__(self, ttl_seconds: float = 300.0, max_entries: int = 5000) -> None:
        self.ttl = max(5.0, float(ttl_seconds))
        self.max_entries = max(100, int(max_entries))
        self._items: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get(self, subject: str, method: str, key: str) -> dict[str, Any] | None:
        if not key:
            return None
        now = time.monotonic()
        cache_key = (subject, method, key)
        with self._lock:
            item = self._items.get(cache_key)
            if not item:
                return None
            if item[0] <= now:
                self._items.pop(cache_key, None)
                return None
            return item[1]

    def put(self, subject: str, method: str, key: str, value: dict[str, Any]) -> None:
        if not key:
            return
        with self._lock:
            if len(self._items) >= self.max_entries:
                oldest = min(self._items.items(), key=lambda item: item[1][0])[0]
                self._items.pop(oldest, None)
            self._items[(subject, method, key)] = (time.monotonic() + self.ttl, value)


class ProductionGuard:
    def __init__(self) -> None:
        self.auth_token = os.getenv("SAREMBOK_AUTH_TOKEN", "").strip()
        self.admin_token = os.getenv("SAREMBOK_ADMIN_TOKEN", "").strip()
        self.master_token = os.getenv("SAREMBOK_MASTER_TOKEN", "").strip()
        self.worker_enrollment_token = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip()
        self.require_origin = os.getenv("SAREMBOK_REQUIRE_ORIGIN", "true").strip().lower() not in {"0", "false", "no"}
        self.allow_originless_local = os.getenv("SAREMBOK_ALLOW_ORIGINLESS_LOCAL", "true").strip().lower() in {"1", "true", "yes"}
        self.public_host = os.getenv("SAREMBOK_PUBLIC_HOST", os.getenv("SAREMBOK_SITE_ADDRESS", "sarembok.com")).strip().lower()
        self.per_ip = FixedWindowRateLimiter(os.getenv("SAREMBOK_RATE_LIMIT_PER_IP", "120"), os.getenv("SAREMBOK_RATE_LIMIT_WINDOW_SECONDS", "60"))
        self.per_subject = FixedWindowRateLimiter(os.getenv("SAREMBOK_RATE_LIMIT_PER_SUBJECT", "180"), os.getenv("SAREMBOK_RATE_LIMIT_SUBJECT_WINDOW_SECONDS", "60"))
        self.idempotency = IdempotencyCache(os.getenv("SAREMBOK_IDEMPOTENCY_TTL_SECONDS", "300"))

    def origin_allowed(self, websocket: Any) -> bool:
        if not self.require_origin:
            return True
        headers = getattr(websocket, "request_headers", {}) or {}
        origin = str(headers.get("Origin", "")).strip()
        if not origin:
            host = str(headers.get("Host", "")).lower()
            if self.allow_originless_local and (host.startswith("127.0.0.1") or host.startswith("localhost")):
                return True
            return False
        allowed = {
            f"https://{self.public_host}",
            f"https://www.{self.public_host}",
            "http://127.0.0.1:9000",
            "http://localhost:9000",
            "http://127.0.0.1",
            "http://localhost",
        }
        return origin.lower().rstrip("/") in {x.rstrip("/") for x in allowed}

    def client_key(self, websocket: Any) -> str:
        peer = getattr(websocket, "remote_address", None)
        if isinstance(peer, (tuple, list)) and peer:
            return str(peer[0])
        return str(peer or "unknown")

    def identify(self, params: dict[str, Any]) -> Identity:
        token = str(params.get("sessionToken") or params.get("authToken") or "").strip()
        if token and self.master_token and hmac.compare_digest(token, self.master_token):
            return Identity("MASTER", "master", _hash(token)[:12])
        if token and self.admin_token and hmac.compare_digest(token, self.admin_token):
            return Identity("ADMIN", "admin", _hash(token)[:12])
        if token and self.auth_token and hmac.compare_digest(token, self.auth_token):
            return Identity("OPERATOR", "runtime", _hash(token)[:12])
        return Identity("PUBLIC", "anonymous", _hash(token)[:12] if token else "")

    def require(self, method: str, params: dict[str, Any], identity: Identity, cloud_server: Any) -> None:
        # Let the runtime's established browser-session check remain authoritative
        # for session-bearing browser requests, then apply least-privilege method policy.
        if method in LOGIN_METHODS:
            if method == "VerifyAdminPasscode":
                # Never accept the historical source fallback. Explicit environment
                # configuration is required before any admin verification can occur.
                configured = str(os.getenv("SAREMBOK_ADMIN_PASSCODE", "")).strip()
                if not configured:
                    raise PermissionError("admin_authentication_not_configured")
                supplied = str(params.get("passcode") or "").strip()
                if not supplied or not hmac.compare_digest(supplied, configured):
                    raise PermissionError("invalid_admin_credentials")
                return
            return

        # Worker API is separately authenticated with a worker token validated by
        # worker_control.py; the guard only requires worker identity marker here.
        if method in WORKER_METHODS:
            if method == "RegisterWorker":
                enrollment = str(params.get("enrollmentToken") or "").strip()
                if not self.worker_enrollment_token or not enrollment or not hmac.compare_digest(enrollment, self.worker_enrollment_token):
                    raise PermissionError("worker_enrollment_required")
                return
            if identity.role not in {"WORKER", "ADMIN", "MASTER", "SYSTEM"}:
                raise PermissionError("worker_authorization_required")
            return

        required = DEFAULT_ROLE_REQUIREMENTS.get(method)
        if required is None:
            if identity.role not in {"ADMIN", "MASTER", "SYSTEM"}:
                raise PermissionError("method_not_exposed_to_browser")
            return
        hierarchy = {"PUBLIC": 0, "USER": 1, "WORKER": 2, "OPERATOR": 3, "ADMIN": 4, "MASTER": 5, "SYSTEM": 6}
        effective = identity.role
        # A normal browser session is reclassified as USER by the production entrypoint.
        if effective == "PUBLIC":
            raise PermissionError("authenticated_session_required")
        if hierarchy.get(effective, 0) < hierarchy.get(required, 1):
            raise PermissionError("insufficient_privilege")

    def rate_limit(self, websocket: Any, identity: Identity) -> None:
        ok, retry = self.per_ip.allow(self.client_key(websocket))
        if not ok:
            raise PermissionError(f"rate_limited_retry_after={retry}")
        ok, retry = self.per_subject.allow(identity.subject)
        if not ok:
            raise PermissionError(f"rate_limited_retry_after={retry}")

    def log_event(self, logger: Any, event: str, **fields: Any) -> None:
        payload = {"event": event, **scrub(fields)}
        logger.info(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))

    @staticmethod
    def error_payload(code: int, message: str, *, data: dict[str, Any] | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"code": code, "message": message}
        if data:
            out["data"] = scrub(data)
        return out
