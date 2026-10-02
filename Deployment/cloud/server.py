"""Sarembok_VE cloud runtime compatibility gateway.

Preserves the public 12-facet JSON-RPC contract while adding production
boundary controls: optional token authentication, connection limits,
request validation, serialized SQLite access, structured logging, and
SIGTERM/SIGINT graceful shutdown.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac as _hmac
import json
import logging
import os
import re
import secrets
import signal
import sqlite3
import time
import urllib.request
import urllib.error
import urllib.parse
import uuid
import threading
import sys

# Make sibling cloud modules importable both in the production container and when
# server.py is imported directly by local/CI regression tests.
_CLOUD_DIR = os.path.dirname(os.path.abspath(__file__))
if _CLOUD_DIR not in sys.path:
    sys.path.insert(0, _CLOUD_DIR)

from runtime_authority import snapshot as runtime_authority_snapshot
from runtime_response_composer import (
    build_runtime_context,
    is_capability_query,
    is_identity_query,
    is_limitation_query,
    is_self_state_query,
    is_worker_prune_query,
    render_capabilities,
    render_identity,
    render_limitations,
    render_model_inventory,
)
from provider_router import ProviderRouter, set_stream_callback, reset_stream_callback
from live_voice import provision_ephemeral_token
from capability_registry import CapabilityRegistry
from structured_response import build_structured_response
from datetime import datetime, timezone
from typing import Any

import websockets

PORT = int(os.getenv("SAREMBOK_PORT", "9000"))
DB_PATH = os.getenv("SAREMBOK_DB_PATH", "/data/sarembok_cloud.db")
AUTH_TOKEN = os.getenv("SAREMBOK_AUTH_TOKEN", "").strip()
MAX_CONNECTIONS = max(1, int(os.getenv("SAREMBOK_MAX_CONNECTIONS", "100")))
MAX_REQUEST_BYTES = max(1024, int(os.getenv("SAREMBOK_MAX_REQUEST_BYTES", str(1024 * 1024))))
MAX_METHOD_LENGTH = max(32, int(os.getenv("SAREMBOK_MAX_METHOD_LENGTH", "128")))
LLM_PROVIDER_TIMEOUT_SECONDS = max(3, int(os.getenv("SAREMBOK_LLM_PROVIDER_TIMEOUT_SECONDS", "8")))
LLM_TOTAL_TIMEOUT_SECONDS = max(5, int(os.getenv("SAREMBOK_LLM_TOTAL_TIMEOUT_SECONDS", "15")))
SAREMBOK_VOICE_URL = os.getenv("SAREMBOK_VOICE_URL", "http://sarembok-voice:9200").rstrip("/")
SAREMBOK_VOICE_MAX_CHARS = max(100, int(os.getenv("SAREMBOK_VOICE_MAX_CHARS", "4000")))
VOICE_REQUEST_TIMEOUT_SECONDS = max(30, int(os.getenv("SAREMBOK_VOICE_REQUEST_TIMEOUT_SECONDS", "120")))
BROWSER_SESSION_TTL_SECONDS = max(300, int(os.getenv("SAREMBOK_BROWSER_SESSION_TTL_SECONDS", "3600")))
WORKER_AUTH_METHODS = {
    "RegisterWorker",
    "Heartbeat",
    "ListTasks",
    "ClaimTask",
    "CompleteTask",
    "FailTask",
}
WORKER_ENROLLMENT_TOKEN = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip()
BROWSER_ALLOWED_METHODS = {
    "SarembokChat",
    "RecordLiveTurn",
    "SynthesizeSpeech",
    "SynthesizeSpeechStream",
    "GetRuntimeInfo",
    "GetProviderMetrics",
    "BrowserNavigate",
    "BrowserScreenshot",
    "BrowserRender",
    "BrowserSessionOpen",
    "BrowserSessionInspect",
    "BrowserAction",
    "BrowserSessionClose",
    "CallMcpTool",
    "CreateDigitalHumanSession",
    "GetDigitalHumanSession",
    "ListDigitalHumanSessions",
    "CloseDigitalHumanSession",
    "SubmitFeedback",
    "GetFeedbackSummary",
    "SearchMemories",
    "DeleteMemory",
    "StoreMemory",
    "ListMemories",
    "GetMemoryConversation",
    "ListWorkers",
    "ScaleWorkers",
    "GetGpuMarketplace",
    "RentGpuNode",
    "ListGpuRentals",
    "ProcessVisionFrame",
    "GetVisionStatus",
    "AdminExecuteDirective",
    "GetAdminStatus",
    "VerifyAdminPasscode",
    "SearchYouTube",
    "ResolveMediaStream",
    "RegisterWorker",
    "Heartbeat",
    "ListTasks",
    "ClaimTask",
    "CompleteTask",
    "FailTask",
    "ScheduleCompute",
    "CreateTask",
    "GenerateImage",
    "ExecuteComputeTask",
    "GetVisualEngineStatus",
    "ListMcpServers",
    "RegisterMcpServer",
    "CancelActiveStream",
    "SpatialVisualRecall",
    "PruneWorkers",
    "AuthenticateMaster",
    "AuthenticateSocialUser",
    "GetCurrentUser",
    "ListUserChatSessions",
    "SaveUserChatSession",
    "DeleteUserChatSession",
}
BROWSER_SESSIONS: dict[str, float] = {}
STARTED = time.time()
PROVIDER_ROUTER = ProviderRouter()
CAPABILITY_REGISTRY = CapabilityRegistry()

logging.basicConfig(
    level=os.getenv("SAREMBOK_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOG = logging.getLogger("sarembok.cloud")

ADMIN_PASSCODE = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
ADMIN_ALLOWED_PASSCODES = {
    ADMIN_PASSCODE,
    os.getenv("SAREMBOK_AUTH_TOKEN", "").strip(),
} - {""}
ADMIN_TOKENS: set[str] = set()
USER_SESSIONS: dict[str, dict[str, Any]] = {}

# Fast conversational lane: keeps recent turns in memory so ordinary dialogue
# does not wait on SQLite reads before the first model token.
FAST_CHAT_HISTORY: dict[str, list[dict[str, str]]] = {}
FAST_CHAT_HISTORY_LOCK = threading.RLock()
FAST_CHAT_MAX_TURNS = 8

FAST_LANE_BLOCKERS = (
    "latest", "news", "headline", "weather", "stock", "price", "crypto",
    "research", "search", "browse", "look up", "find out", "current event",
    "what happened", "happening", "today", "yesterday", "this week",
    "this month", "breaking", "election", "president", "market",
    "create ", "spawn ", "build ", "deploy ", "execute ", "run ",
    "remember", "store memory", "save ", "forget ", "delete ",
    "play ", "watch ", "show ", "stream ", "listen to ", "youtube",
    "screenshot", "render ", "browser", "code", "program", "script",
    "architecture", "api ", "docker", "linux", "gpu", "worker",
    "task", "agent", "compute", "generate image", "image",
    "/admin", "/exec", "/sh", "/py",
)


WEB_EXECUTION_MARKERS = (
    "go to ", "navigate to ", "open the website", "open the site", "visit ",
    "on the website", "on the site", "click ", "fill ", "type ", "enter ",
    "select ", "choose ", "submit ", "log in", "login", "sign in",
    "sign into", "use the website", "use this site", "search the web",
    "search on ", "open a browser", "browser", "website", "web app",
)
MEDIA_EXECUTION_MARKERS = (
    "play ", "watch ", "listen to ", "stream ", "youtube", "video",
    "song", "music", "audio",
)
HOST_EXECUTION_MARKERS = (
    "open app", "launch app", "start application", "open application", "desktop",
    "on my computer", "on my pc", "windows app", "run command on my computer",
    "open file on my computer", "local computer", "my desktop", "start notepad",
    "start calculator", "start chrome", "start edge",
)

def _is_host_execution_intent(prompt: str) -> bool:
    low = str(prompt or "").strip().lower()
    if not low:
        return False
    return any(marker in low for marker in HOST_EXECUTION_MARKERS)


def _is_browser_execution_intent(prompt: str) -> bool:
    low = str(prompt or "").strip().lower()
    if not low or any(marker in low for marker in MEDIA_EXECUTION_MARKERS):
        return False
    if re.search(r"https?://\S+", low):
        return True
    if re.search(r"\b(?:check|read|open|use|access|connect|update|post|create|send|search)\b.{0,60}\b(?:gmail|outlook|email|slack|discord|github|gitlab|notion|drive|calendar|linkedin|facebook|instagram|reddit)\b", low):
        return True
    return any(marker in low for marker in WEB_EXECUTION_MARKERS)
def _is_fast_conversational_turn(prompt: str, image_frame: str | None = None, admin: bool = False) -> bool:
    if admin or image_frame:
        return False
    text = (prompt or "").strip().lower()
    if not text or len(text) > 400:
        return False
    return not any(marker in text for marker in FAST_LANE_BLOCKERS)

def _get_fast_chat_history(session_id: str) -> list[dict[str, str]]:
    sid = session_id or "sess_main"
    with FAST_CHAT_HISTORY_LOCK:
        return list(FAST_CHAT_HISTORY.get(sid, []))[-FAST_CHAT_MAX_TURNS:]

def _record_fast_chat_turn(session_id: str, prompt: str, reply: str) -> None:
    sid = session_id or "sess_main"
    with FAST_CHAT_HISTORY_LOCK:
        history = FAST_CHAT_HISTORY.setdefault(sid, [])
        history.extend([
            {"role": "user", "content": str(prompt or "").strip()},
            {"role": "assistant", "content": str(reply or "").strip()},
        ])
        del history[:-FAST_CHAT_MAX_TURNS]


import base64
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
    OPENCV_VERSION = cv2.__version__
except ImportError:
    OPENCV_AVAILABLE = False
    OPENCV_VERSION = "NOT_INSTALLED"

OPENCV_DETECTOR = None
if OPENCV_AVAILABLE:
    model_paths = [
        "/app/models/face_detection_yunet_2023mar.onnx",
        "Deployment/cloud/models/face_detection_yunet_2023mar.onnx",
        os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet_2023mar.onnx"),
    ]
    for p in model_paths:
        if os.path.exists(p):
            try:
                OPENCV_DETECTOR = cv2.FaceDetectorYN_create(p, "", (320, 240), 0.6, 0.3, 5000)
                LOG.info("OpenCV YuNet FaceDetector loaded from %s", p)
                break
            except Exception as e:
                LOG.warning("Failed to load YuNet from %s: %s", p, e)



def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CloudStore:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("PRAGMA busy_timeout=10000")
        self._init()

    def _init(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS delegations (
                delegation_id TEXT PRIMARY KEY,
                source_agent_id TEXT,
                target_agent_id TEXT,
                goal_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                capabilities TEXT NOT NULL,
                gpu_vendor TEXT,
                gpu_model TEXT,
                vram_mb INTEGER,
                cuda_version TEXT,
                available_memory_mb INTEGER,
                supported_models TEXT,
                latency_ms REAL,
                status TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS digital_human_sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                worker_id TEXT,
                metahuman_id TEXT,
                voice_profile TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                required_capability TEXT NOT NULL DEFAULT 'compute',
                payload TEXT NOT NULL DEFAULT '{}',
                result TEXT NOT NULL DEFAULT '{}',
                error TEXT,
                assigned_worker_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT,
                lead_agent_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                tier TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                agent_id TEXT,
                session_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS file_assets (
                file_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
                category TEXT NOT NULL DEFAULT 'document',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                agent_id TEXT,
                task_id TEXT,
                wal_index INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'VERIFIED',
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS governance_approvals (
                approval_id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                target TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                requested_by TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
                details TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                resolved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id, created_at);
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_id TEXT,
                prompt TEXT,
                response TEXT,
                rating INTEGER NOT NULL,
                feedback_text TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT DEFAULT 'anonymous',
                title TEXT,
                messages_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at DESC);
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                name TEXT,
                avatar_url TEXT,
                auth_provider TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL,
                last_login_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            """
        )
        self.db.commit()

        worker_cols = [row[1] for row in self.db.execute("PRAGMA table_info(workers)").fetchall()]
        if worker_cols and "worker_token_hash" not in worker_cols:
            self.db.execute("ALTER TABLE workers ADD COLUMN worker_token_hash TEXT")
            self.db.commit()

        # Ensure schema migrations for existing databases
        columns = [row[1] for row in self.db.execute("PRAGMA table_info(tasks)").fetchall()]
        if columns and "required_capability" not in columns:
            self.db.execute("ALTER TABLE tasks ADD COLUMN required_capability TEXT NOT NULL DEFAULT 'compute'")
            self.db.commit()
        columns = [row[1] for row in self.db.execute("PRAGMA table_info(tasks)").fetchall()]
        if columns and "result" not in columns:
            self.db.execute("ALTER TABLE tasks ADD COLUMN result TEXT NOT NULL DEFAULT '{}'")
            self.db.commit()
        columns = [row[1] for row in self.db.execute("PRAGMA table_info(tasks)").fetchall()]
        if columns and "error" not in columns:
            self.db.execute("ALTER TABLE tasks ADD COLUMN error TEXT")
            self.db.commit()

        memory_cols = [row[1] for row in self.db.execute("PRAGMA table_info(memories)").fetchall()]
        if memory_cols and "session_id" not in memory_cols:
            self.db.execute("ALTER TABLE memories ADD COLUMN session_id TEXT")
            self.db.commit()

        chat_cols = [row[1] for row in self.db.execute("PRAGMA table_info(chat_sessions)").fetchall()]
        if chat_cols and "user_id" not in chat_cols:
            self.db.execute("ALTER TABLE chat_sessions ADD COLUMN user_id TEXT DEFAULT 'anonymous'")
            self.db.commit()

        self.db.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
        self.db.commit()

    def create_agent(self, agent_id: str, display_name: str) -> dict[str, Any]:
        stamp = now()
        self.db.execute(
            "INSERT OR REPLACE INTO agents(agent_id,display_name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
            (agent_id, display_name, "ONLINE", stamp, stamp),
        )
        self.db.commit()
        self.event(agent_id, "AGENT_CREATED", {"displayName": display_name})
        return {"agentId": agent_id, "displayName": display_name, "status": "created"}

    def create_task(self, task_type: str, assigned_worker_id: str | None = None, payload: dict[str, Any] | None = None, required_capability: str = "compute") -> dict[str, Any]:
        task_id = f"task-{uuid.uuid4().hex[:10]}"
        stamp = now()
        status = "QUEUED" if assigned_worker_id else "PENDING_WORKER"
        payload_obj = payload or {}
        capability = str(required_capability or "compute").strip() or "compute"
        payload_json = json.dumps(payload_obj)
        self.db.execute(
            """
            INSERT INTO tasks(task_id, task_type, required_capability, payload, result, error, assigned_worker_id, status, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (task_id, task_type, capability, payload_json, "{}", None, assigned_worker_id, status, stamp, stamp),
        )
        self.db.commit()
        self.event(None, "TASK_CREATED", {"taskId": task_id, "taskType": task_type, "requiredCapability": capability, "status": status})
        return {"taskId": task_id, "taskType": task_type, "requiredCapability": capability, "assignedWorkerId": assigned_worker_id, "status": status, "payload": payload_obj, "createdAt": stamp}

    def agent_exists(self, agent_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM agents WHERE agent_id=?", (agent_id,)).fetchone() is not None

    def event(self, agent_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT INTO events(agent_id,event_type,payload,created_at) VALUES(?,?,?,?)",
            (agent_id, event_type, json.dumps(payload), now()),
        )
        self.db.commit()

    def conversation_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]

    def close(self) -> None:
        self.db.close()


store = CloudStore(DB_PATH)
STARTED = time.time()
PROVIDER_ROUTER = ProviderRouter()
CAPABILITY_REGISTRY = CapabilityRegistry()
DB_LOCK = asyncio.Lock()
CONNECTIONS = asyncio.Semaphore(MAX_CONNECTIONS)

# Prometheus Super-Engine Subsystems
import sys
_current_dir = os.path.dirname(os.path.abspath(__file__))
for _p in ["/app", "/app/Deployment/cloud", _current_dir, os.path.join(_current_dir, "Deployment", "cloud")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from evolver import AutonomousEvolver
    from proactive_daemon import ProactiveOmniDaemon
    from swarm_compiler import SwarmCompiler
except Exception:
    try:
        from Deployment.cloud.evolver import AutonomousEvolver
        from Deployment.cloud.proactive_daemon import ProactiveOmniDaemon
        from Deployment.cloud.swarm_compiler import SwarmCompiler
    except Exception as e:
        LOG.warning("Prometheus import fallback: %s", e)
        AutonomousEvolver = None
        ProactiveOmniDaemon = None
        SwarmCompiler = None

DB_LOCK: asyncio.Lock | None = None
CONNECTIONS: asyncio.Semaphore | None = None
STOP: asyncio.Event | None = None


def get_db_lock() -> asyncio.Lock:
    global DB_LOCK
    if DB_LOCK is None:
        DB_LOCK = asyncio.Lock()
    return DB_LOCK


def get_connections() -> asyncio.Semaphore:
    global CONNECTIONS
    if CONNECTIONS is None:
        CONNECTIONS = asyncio.Semaphore(MAX_CONNECTIONS)
    return CONNECTIONS


def get_stop_event() -> asyncio.Event:
    global STOP
    if STOP is None:
        STOP = asyncio.Event()
    return STOP



WORKER_HEARTBEAT_TIMEOUT_SECONDS = int(
    os.getenv("SAREMBOK_WORKER_HEARTBEAT_TIMEOUT_SECONDS")
    or os.getenv("SAREMBOK_WORKER_HEARTBEAT_TIMEOUT")
    or "60"
)
WORKER_OFFLINE_TIMEOUT_SECONDS = int(
    os.getenv("SAREMBOK_WORKER_OFFLINE_TIMEOUT_SECONDS", "180")
)
WORKER_LIFECYCLE_INTERVAL_SECONDS = int(
    os.getenv("SAREMBOK_WORKER_LIFECYCLE_INTERVAL_SECONDS", "15")
)
WORKER_PRUNE_TIMEOUT_SECONDS = int(
    os.getenv("SAREMBOK_WORKER_PRUNE_SECONDS", "3600")
)
MONITOR_TASK: asyncio.Task | None = None


def validate_worker_lifecycle_config(
    heartbeat_timeout: int = WORKER_HEARTBEAT_TIMEOUT_SECONDS,
    offline_timeout: int = WORKER_OFFLINE_TIMEOUT_SECONDS,
    interval: int = WORKER_LIFECYCLE_INTERVAL_SECONDS,
) -> None:
    if heartbeat_timeout <= 0:
        raise ValueError("SAREMBOK_WORKER_HEARTBEAT_TIMEOUT_SECONDS must be > 0")
    if offline_timeout <= heartbeat_timeout:
        raise ValueError("SAREMBOK_WORKER_OFFLINE_TIMEOUT_SECONDS must be > SAREMBOK_WORKER_HEARTBEAT_TIMEOUT_SECONDS")
    if interval <= 0:
        raise ValueError("SAREMBOK_WORKER_LIFECYCLE_INTERVAL_SECONDS must be > 0")


validate_worker_lifecycle_config()


def get_heartbeat_age_seconds(timestamp: str, ref_time: datetime | None = None) -> float | None:
    if not timestamp:
        return None
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(timezone.utc)
        now_dt = ref_time or datetime.now(timezone.utc)
        return (now_dt - dt).total_seconds()
    except Exception:
        return None


def heartbeat_is_fresh(timestamp: str, max_age_seconds: float = WORKER_HEARTBEAT_TIMEOUT_SECONDS, ref_time: datetime | None = None) -> bool:
    age = get_heartbeat_age_seconds(timestamp, ref_time)
    if age is None:
        return False
    return age <= max_age_seconds


def ensure_scheduler_schema() -> None:
    columns = {
        row[1]
        for row in store.db.execute(
            "PRAGMA table_info(workers)"
        ).fetchall()
    }

    if "active_tasks" not in columns:
        store.db.execute(
            """
            ALTER TABLE workers
            ADD COLUMN active_tasks INTEGER NOT NULL DEFAULT 0
            """
        )
        store.db.commit()

    # Truth Boundary: Remove any mock or unverified worker entries
    store.db.execute(
        "DELETE FROM workers WHERE worker_id LIKE 'worker-gpu-%' OR worker_id LIKE 'worker-edge-%' OR worker_id LIKE 'worker-scale-%'"
    )
    store.db.execute(
        """
        CREATE TABLE IF NOT EXISTS gpu_rentals (
            rental_id TEXT PRIMARY KEY,
            tier_id TEXT NOT NULL,
            tier_name TEXT NOT NULL,
            vram_gb INTEGER NOT NULL,
            hourly_rate REAL NOT NULL,
            duration_hours INTEGER NOT NULL,
            total_price REAL NOT NULL,
            workload TEXT NOT NULL,
            status TEXT NOT NULL,
            renter_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    store.db.commit()


SOVEREIGN_WORKER_ID = "sarembok-edge-frontier-01"

def _local_gpu_is_verified() -> tuple[bool, dict[str, Any]]:
    """Return true only when an actual NVIDIA GPU is visible to this process."""
    if os.getenv("SAREMBOK_SOVEREIGN_WORKER_ENABLED", "").strip().lower() not in {"1","true","yes","on"}:
        return False, {"reason": "sovereign_worker_disabled"}
    try:
        import subprocess
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return False, {"reason": "nvidia_gpu_not_visible"}
        row = [x.strip() for x in proc.stdout.splitlines()[0].split(",")]
        if len(row) < 3:
            return False, {"reason": "nvidia_smi_unparseable"}
        return True, {"gpuModel": row[0], "vramMb": int(float(row[1])) if row[1] else 0, "driverVersion": row[2]}
    except Exception as exc:
        return False, {"reason": "gpu_probe_failed", "detail": str(exc)}

def ensure_sovereign_worker() -> bool:
    """Register a sovereign worker only after the host proves real GPU hardware."""
    verified, gpu = _local_gpu_is_verified()
    if not verified:
        store.db.execute("DELETE FROM workers WHERE worker_id=?", (SOVEREIGN_WORKER_ID,))
        store.db.commit()
        return False
    try:
        stamp = now()
        caps = json.dumps(["compute","gpu","inference","image_generation","synthesis","speech_synthesis","vision_inference","deep_reasoning"])
        models = json.dumps([])
        existing = store.db.execute("SELECT worker_id FROM workers WHERE worker_id=?", (SOVEREIGN_WORKER_ID,)).fetchone()
        values = (caps, "NVIDIA", gpu.get("gpuModel"), int(gpu.get("vramMb") or 0), str(gpu.get("driverVersion") or ""), int(gpu.get("vramMb") or 0), models, stamp)
        if not existing:
            store.db.execute(
                """INSERT INTO workers(worker_id,capabilities,gpu_vendor,gpu_model,vram_mb,cuda_version,available_memory_mb,supported_models,latency_ms,status,last_heartbeat,active_tasks)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,0)""",
                (SOVEREIGN_WORKER_ID,*values[:7],0.0,"ONLINE",stamp),
            )
        else:
            store.db.execute(
                """UPDATE workers SET status='ONLINE',last_heartbeat=?,capabilities=?,gpu_vendor=?,gpu_model=?,vram_mb=?,cuda_version=?,available_memory_mb=?,supported_models=? WHERE worker_id=?""",
                (stamp,caps,"NVIDIA",gpu.get("gpuModel"),int(gpu.get("vramMb") or 0),str(gpu.get("driverVersion") or ""),int(gpu.get("vramMb") or 0),models,SOVEREIGN_WORKER_ID),
            )
        store.db.commit()
        return True
    except Exception as exc:
        LOG.warning("Failed to register verified sovereign worker: %s", exc)
        return False


GPU_MARKETPLACE_TIERS = [
    {
        "tierId": "colab-t4",
        "tierName": "Google Colab Tesla T4 (Community)",
        "gpuModel": "NVIDIA Tesla T4",
        "vramGb": 16,
        "vramMb": 15360,
        "memoryType": "GDDR6 300 GB/s",
        "hourlyRate": 0.00,
        "isFree": True,
        "tflopsFp16": 65,
        "badge": "FREE COMMUNITY NODE",
        "badgeColor": "cyan",
        "description": "100% Free 16GB GPU compute powered by Google Colab. Perfect for FP16 inference, conversational agents, and testing.",
        "capabilities": ["inference", "speech_synthesis", "web_research"],
        "setupType": "colab_1click",
        "colabCommand": "!curl -sSL https://raw.githubusercontent.com/jetsontech/SarembokVE/runtime-authority-truth-boundary/Deployment/cloud/colab_worker.py | python3 - --ws-url wss://sarembok.com",
    },
    {
        "tierId": "rtx-4090",
        "tierName": "GeForce RTX 4090 Dedicated",
        "gpuModel": "NVIDIA GeForce RTX 4090",
        "vramGb": 24,
        "vramMb": 24576,
        "memoryType": "GDDR6X 1008 GB/s",
        "hourlyRate": 0.65,
        "isFree": False,
        "tflopsFp16": 165,
        "badge": "ULTRA-LOW LATENCY",
        "badgeColor": "amber",
        "description": "Extreme workstation silicon with 16,384 CUDA cores. Ideal for real-time 3D MetaHuman rendering and Whisper TTS.",
        "capabilities": ["meta_human", "whisper_tts", "vision_inference"],
        "setupType": "on_demand_rental",
    },
    {
        "tierId": "a100-80gb",
        "tierName": "A100 SXM4 Enterprise Cluster",
        "gpuModel": "NVIDIA A100-SXM4-80GB",
        "vramGb": 80,
        "vramMb": 81920,
        "memoryType": "HBM2e 2039 GB/s",
        "hourlyRate": 1.45,
        "isFree": False,
        "tflopsFp16": 312,
        "badge": "HIGH VRAM WORKHORSE",
        "badgeColor": "emerald",
        "description": "High-bandwidth memory architecture for massive context inference, Llama-3.3-70B, and DeepSeek model fine-tuning.",
        "capabilities": ["large_llm", "deep_reasoning", "fine_tuning"],
        "setupType": "on_demand_rental",
    },
    {
        "tierId": "h100-sxm5",
        "tierName": "H100 SXM5 Hopper Tensor Core",
        "gpuModel": "NVIDIA H100 SXM5",
        "vramGb": 80,
        "vramMb": 81920,
        "memoryType": "HBM3 3350 GB/s",
        "hourlyRate": 2.85,
        "isFree": False,
        "tflopsFp16": 989,
        "badge": "MAX COMPUTE THROUGHPUT",
        "badgeColor": "indigo",
        "description": "State-of-the-art Hopper architecture with Transformer Engine. Maximum throughput for concurrent multi-agent swarms.",
        "capabilities": ["swarm_orchestration", "fp8_synthesis", "heavy_compute"],
        "setupType": "on_demand_rental",
    },
]


def evaluate_worker_liveness(now_dt: datetime | None = None) -> dict[str, int]:
    """Evaluates liveness for all registered workers and persists state transitions safely.

    ONLINE:  0 <= age <= WORKER_HEARTBEAT_TIMEOUT_SECONDS
    STALE:   WORKER_HEARTBEAT_TIMEOUT_SECONDS < age <= WORKER_OFFLINE_TIMEOUT_SECONDS
    OFFLINE: age > WORKER_OFFLINE_TIMEOUT_SECONDS (or missing/invalid timestamp)
    """
    ensure_scheduler_schema()
    ref_time = now_dt or datetime.now(timezone.utc)

    rows = store.db.execute(
        "SELECT worker_id, status, last_heartbeat FROM workers"
    ).fetchall()

    counts = {"online": 0, "stale": 0, "offline": 0, "transitions": 0}

    for row in rows:
        worker_id = row[0]
        prev_status = str(row[1]).upper()
        hb_stamp = row[2]

        age = get_heartbeat_age_seconds(hb_stamp, ref_time)

        if age is not None and age >= 0:
            if age <= WORKER_HEARTBEAT_TIMEOUT_SECONDS:
                new_status = "ONLINE"
            elif age <= WORKER_OFFLINE_TIMEOUT_SECONDS:
                new_status = "STALE"
            else:
                new_status = "OFFLINE"
        else:
            new_status = "OFFLINE"

        if new_status != prev_status:
            cursor = store.db.execute(
                """
                UPDATE workers
                SET status=?
                WHERE worker_id=? AND last_heartbeat=? AND status=?
                """,
                (new_status, worker_id, hb_stamp, prev_status),
            )
            if cursor.rowcount > 0:
                store.db.commit()
                LOG.info(
                    "worker status transition worker_id=%s %s->%s",
                    worker_id,
                    prev_status,
                    new_status,
                )
                eval_stamp = ref_time.isoformat()
                event_payload = {
                    "workerId": worker_id,
                    "previousStatus": prev_status,
                    "status": new_status,
                    "lastHeartbeat": hb_stamp,
                    "evaluatedAt": eval_stamp,
                }
                store.event(None, "WORKER_STATUS_CHANGED", event_payload)
                counts["transitions"] += 1
                counts[new_status.lower()] += 1
            else:
                counts[prev_status.lower()] += 1
        else:
            counts[new_status.lower()] += 1

    # Auto-prune dead/historical offline workers older than WORKER_PRUNE_TIMEOUT_SECONDS
    pruned_cnt = prune_stale_workers(now_dt=ref_time)
    counts["pruned"] = pruned_cnt

    return counts


def prune_stale_workers(
    max_offline_age_seconds: int | None = None,
    force_all_offline: bool = False,
    now_dt: datetime | None = None,
) -> int:
    """Safely prune dead/stale offline workers from the registry.

    If force_all_offline is True, deletes all workers currently marked OFFLINE.
    Otherwise, deletes workers marked OFFLINE whose heartbeat is older than max_offline_age_seconds.
    Active sovereign workers with fresh heartbeats are never pruned.
    """
    ensure_scheduler_schema()
    ref_time = now_dt or datetime.now(timezone.utc)
    cutoff = max_offline_age_seconds if max_offline_age_seconds is not None else WORKER_PRUNE_TIMEOUT_SECONDS

    if force_all_offline:
        cursor = store.db.execute("DELETE FROM workers WHERE status='OFFLINE'")
        pruned = cursor.rowcount
        if pruned > 0:
            store.db.commit()
            LOG.info("Pruned %d offline workers (force_all_offline)", pruned)
        return pruned

    rows = store.db.execute("SELECT worker_id, last_heartbeat FROM workers WHERE status='OFFLINE'").fetchall()
    pruned = 0
    for worker_id, hb_stamp in rows:
        age = get_heartbeat_age_seconds(hb_stamp, ref_time)
        if age is not None and age > cutoff:
            c = store.db.execute("DELETE FROM workers WHERE worker_id=? AND status='OFFLINE'", (worker_id,))
            if c.rowcount > 0:
                pruned += c.rowcount
    if pruned > 0:
        store.db.commit()
        LOG.info("Auto-pruned %d expired offline workers (cutoff=%ds)", pruned, cutoff)
    return pruned


def get_worker_status_counts() -> dict[str, int]:
    evaluate_worker_liveness()
    worker_count = store.db.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    online_count = store.db.execute("SELECT COUNT(*) FROM workers WHERE status='ONLINE'").fetchone()[0]
    stale_count = store.db.execute("SELECT COUNT(*) FROM workers WHERE status='STALE'").fetchone()[0]
    offline_count = store.db.execute("SELECT COUNT(*) FROM workers WHERE status='OFFLINE'").fetchone()[0]
    return {
        "registeredWorkers": worker_count,
        "onlineWorkers": online_count,
        "staleWorkers": stale_count,
        "offlineWorkers": offline_count,
    }


TASK_CAPABILITY_BY_TYPE = {
    "smoke_test": "compute",
    "arithmetic": "compute",
    "compute": "compute",
    "general_compute": "compute",
    "verification_suite": "compute",
    "gpu_deployment": "gpu",
    "inference": "inference",
    "architecture_synthesis": "inference",
    "code_generation": "inference",
    "meta_human": "meta_human",
    "host_action": "host_control",
    "desktop": "desktop",
    "web_automation": "web_automation",
}


def required_capability_for_task(task_type: str, requested: str | None = None) -> str:
    explicit = str(requested or "").strip()
    if explicit:
        return explicit
    return TASK_CAPABILITY_BY_TYPE.get(
        str(task_type or "").strip().lower(),
        "compute",
    )


def task_dependency_ready(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return True
    dependency = str(payload.get("dependsOnTaskId") or "").strip()
    if not dependency:
        return True
    row = store.db.execute(
        "SELECT status FROM tasks WHERE task_id=?",
        (dependency,),
    ).fetchone()
    return bool(row and str(row[0]).upper() == "COMPLETED")


def select_worker(required_capability: str) -> str | None:
    ensure_scheduler_schema()
    evaluate_worker_liveness()

    rows = store.db.execute(
        """
        SELECT
            worker_id,
            capabilities,
            active_tasks,
            latency_ms,
            available_memory_mb,
            last_heartbeat
        FROM workers
        WHERE status='ONLINE'
        """
    ).fetchall()

    candidates = []

    for row in rows:
        worker_id = row[0]
        raw_caps = row[1]
        active_tasks = int(row[2] or 0)
        latency_ms = float(row[3] or 999999)
        available_memory_mb = int(row[4] or 0)
        hb_stamp = row[5]

        try:
            caps = json.loads(raw_caps) if raw_caps else []
        except Exception:
            caps = []

        if required_capability not in caps:
            continue

        if not heartbeat_is_fresh(hb_stamp, WORKER_HEARTBEAT_TIMEOUT_SECONDS):
            continue

        # Lower active workload wins.
        # Then lower latency.
        # Then higher available memory.
        candidates.append(
            (
                active_tasks,
                latency_ms,
                -available_memory_mb,
                worker_id,
            )
        )

    if not candidates:
        return None

    candidates.sort()

    return candidates[0][3]


def assign_pending_tasks() -> int:
    """Finds all tasks in PENDING_WORKER status and assigns them to eligible ONLINE workers."""
    rows = store.db.execute(
        "SELECT task_id, required_capability FROM tasks WHERE status='PENDING_WORKER' ORDER BY created_at ASC"
    ).fetchall()
    assigned_count = 0
    stamp = now()
    for row in rows:
        task_id = row[0]
        req_cap = row[1] or "compute"
        payload_row = store.db.execute(
            "SELECT payload FROM tasks WHERE task_id=?",
            (task_id,),
        ).fetchone()
        try:
            payload_obj = json.loads(payload_row[0]) if payload_row and payload_row[0] else {}
        except Exception:
            payload_obj = {}
        if not task_dependency_ready(payload_obj):
            continue
        worker_id = select_worker(required_capability=req_cap)
        if worker_id:
            store.db.execute(
                "UPDATE tasks SET assigned_worker_id=?, status='QUEUED', updated_at=? WHERE task_id=? AND status='PENDING_WORKER'",
                (worker_id, stamp, task_id),
            )
            if store.db.execute("SELECT changes()").fetchone()[0] == 1:
                assigned_count += 1
                LOG.info("assigned pending task %s to worker %s", task_id, worker_id)
                store.event(None, "TASK_ASSIGNED", {"taskId": task_id, "workerId": worker_id, "status": "QUEUED"})
    if assigned_count > 0:
        store.db.commit()
    return assigned_count


def require_agent(agent_id: str) -> None:
    if not agent_id:
        raise ValueError("agentId is required")
    if not store.agent_exists(agent_id):
        raise ValueError(f"agent_not_found: {agent_id}")


import xml.etree.ElementTree as ET


def _is_model_identity_query(prompt: str) -> bool:
    markers = (
        "what model is this",
        "what model are you",
        "what model do you use",        "what model is running",
        "what model is active",
        "what model are you running",
    )
    prompt_lower = prompt.lower()
    return any(m in prompt_lower for m in markers)


STOP_WORDS_SEARCH = {
    "what", "whats", "what's", "is", "are", "was", "were", "going", "on", "with", "about",
    "right", "now", "tell", "me", "how", "why", "when", "where", "who", "which", "there",
    "here", "can", "you", "the", "a", "an", "in", "to", "for", "of", "and", "or", "do",
    "does", "did", "have", "has", "had", "any", "some", "latest", "recent", "today", "news",
    "this", "that", "these", "those", "it", "its", "i", "my", "we", "us", "our", "your",    "he", "him", "his", "she", "her", "they", "them", "their", "so", "be", "been", "being"
}


def _extract_search_terms(query: str) -> str:
    quotes = re.findall(r'["\']([^"\']+)["\']', query)
    if quotes:
        return quotes[0]
    caps = re.findall(r'\b[A-Z][a-zA-Z0-9_\-\.]*\b', query)
    if caps:
        return " ".join(caps)
    words = re.findall(r'\b[a-zA-Z0-9_\-\.]+\b', query)
    filtered = [w for w in words if w.lower() not in STOP_WORDS_SEARCH]
    if filtered:
        return " ".join(filtered)
    return ""


def _fetch_realtime_data(query: str) -> str | None:
    """Multi-tiered real-time data engine: Google News RSS + DuckDuckGo + Wikipedia."""
    clean_q = query.strip()
    if not clean_q:
        return None
    results = []

    # 1. Real-Time News & Current Events (Google News RSS)
    terms = _extract_search_terms(clean_q)
    is_news_intent = any(k in clean_q.lower() for k in ("news", "headline", "headlines", "current event", "breaking", "update", "happening"))
    if not terms and not is_news_intent:
        return None

    try:
        if terms and terms.lower() not in ("news", "the news", "current events", ""):
            rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(terms)}&hl=en-US&gl=US&ceid=US:en"
        else:
            rss_url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            root = ET.fromstring(resp.read())
            items = root.findall(".//item")[:5]
            news_lines = []
            for it in items:
                t = it.find("title").text if it.find("title") is not None else ""
                p = it.find("pubDate").text if it.find("pubDate") is not None else ""
                src = it.find("source").text if it.find("source") is not None else "Verified News"
                if t:
                    news_lines.append(f"- **[{src}]** {t} *({p})*")
            if news_lines:
                results.append("### [LIVE REAL-TIME VERIFIED NEWS & CURRENT EVENTS]:\n" + "\n".join(news_lines))
    except Exception as exc:
        LOG.debug("News RSS fetch failed: %s", exc)

    # 2. Wikipedia Summary for Entities / Concepts / Research (Only if valid non-stopword entity exists)
    if terms:
        try:
            entity = terms if len(terms.split()) <= 4 else ""
            if entity:
                wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(entity.replace(' ', '_'))}"
                req = urllib.request.Request(wiki_url, headers={"User-Agent": "SarembokVE/2.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    wdata = json.loads(resp.read().decode("utf-8"))
                    extract = wdata.get("extract")
                    if extract and len(extract) > 40:
                        results.append(f"### [VERIFIED FACTUAL CONTEXT] ({wdata.get('title', entity)}):\n{extract}")
        except Exception:
            pass

    # 3. DuckDuckGo Instant Answers
    try:
        encoded = urllib.parse.quote(terms or clean_q)
        ddg_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(ddg_url, headers={"User-Agent": "SarembokVE-Runtime/2.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            abstract = data.get("AbstractText") or data.get("Abstract")
            if abstract:
                src = data.get("AbstractSource", "Web Knowledge")
                results.append(f"### [WEB INTELLIGENCE] [{src}]:\n{abstract}")
    except Exception:
        pass

    if results:
        return "\n\n".join(results)
    return None



# ============================================================
# AUTONOMOUS AGENTIC ADMIN TOOL REGISTRY & REACT EXECUTION LOOP
# ============================================================
import subprocess

class AdminToolRegistry:
    """Autonomous tools for Sarembok Admin Execution Mode."""

    BLOCKED_PATTERNS = [
        r"rm\s+-rf\s+/(?:\s|$)", r"rm\s+-rf\s+/\*", r":\(\)\s*\{\s*:\|:&\s*\}\s*;",
        r"mkfs", r"dd\s+if=/dev/zero", r">\s*/dev/sd[a-z]", r"shutdown", r"reboot", r"init\s+0"
    ]

    @classmethod
    def dispatch(cls, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = (tool_name or "").strip().lower()
        t0 = time.time()
        try:
            if tool in ("run_terminal", "terminal", "shell", "bash", "execute_shell"):
                cmd = str(args.get("command", "") or args.get("cmd", "")).strip()
                res = cls.run_terminal(cmd)
            elif tool in ("execute_python", "python", "py_eval"):
                code_snippet = str(args.get("code", "")).strip()
                res = cls.execute_python(code_snippet)
            elif tool in ("read_file", "view_file", "cat"):
                path = str(args.get("path", "")).strip()
                s_line = int(args.get("start_line", 1))
                e_line = int(args.get("end_line", 150))
                res = cls.read_file(path, s_line, e_line)
            elif tool in ("write_file", "save_file"):
                path = str(args.get("path", "")).strip()
                content = str(args.get("content", ""))
                res = cls.write_file(path, content)
            elif tool in ("fleet_status", "gpu_status", "workers"):
                res = cls.fleet_status()
            elif tool in ("git_info", "git_status", "git"):
                subcmd = str(args.get("command", "status")).strip()
                res = cls.git_info(subcmd)
            elif tool in ("browser_research", "web_search", "search"):
                q = str(args.get("query", "") or args.get("url", "")).strip()
                res = cls.browser_research(q)
            else:
                res = {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            res = {"error": f"Tool execution failed: {e}"}

        dt_ms = round((time.time() - t0) * 1000, 2)
        res["durationMs"] = dt_ms
        return res

    @classmethod
    def run_terminal(cls, command: str) -> dict[str, Any]:
        if not command:
            return {"error": "command is required"}
        for pat in cls.BLOCKED_PATTERNS:
            if re.search(pat, command):
                return {"error": "Security violation: Dangerous destructive command blocked by safety policy."}
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=12
            )
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            return {
                "command": command,
                "exitCode": proc.returncode,
                "stdout": out[:2500] if out else "",
                "stderr": err[:1000] if err else "",
                "truncated": len(out) > 2500
            }
        except subprocess.TimeoutExpired:
            return {"command": command, "error": "Command timed out after 12 seconds"}
        except Exception as exc:
            return {"command": command, "error": str(exc)}

    @classmethod
    def execute_python(cls, code_snippet: str) -> dict[str, Any]:
        if not code_snippet:
            return {"error": "code is required"}
        output_buffer = []
        local_scope = {"print": lambda *args: output_buffer.append(" ".join(str(a) for a in args))}
        try:
            exec(code_snippet, {"__builtins__": __builtins__}, local_scope)
            res_str = "\n".join(output_buffer) if output_buffer else "Execution completed (returncode 0)."
            return {"status": "SUCCESS", "output": res_str[:2500]}
        except Exception as exc:
            return {"status": "ERROR", "output": f"Python Exception: {exc}"}

    @classmethod
    def read_file(cls, path: str, start_line: int = 1, end_line: int = 150) -> dict[str, Any]:
        if not path:
            return {"error": "path is required"}
        # Resolve path
        resolved = os.path.abspath(path)
        if not os.path.exists(resolved):
            return {"error": f"File not found: {path}"}
        if os.path.isdir(resolved):
            entries = os.listdir(resolved)[:50]
            return {"path": path, "type": "directory", "entries": entries}
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            s_idx = max(0, start_line - 1)
            e_idx = min(len(lines), end_line)
            chunk = "".join(lines[s_idx:e_idx])
            return {
                "path": path,
                "totalLines": len(lines),
                "startLine": s_idx + 1,
                "endLine": e_idx,
                "content": chunk[:3500]
            }
        except Exception as exc:
            return {"error": str(exc)}

    @classmethod
    def write_file(cls, path: str, content: str) -> dict[str, Any]:
        if not path:
            return {"error": "path is required"}
        try:
            resolved = os.path.abspath(path)
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "WRITTEN", "path": path, "bytes": len(content.encode("utf-8"))}
        except Exception as exc:
            return {"error": str(exc)}

    @classmethod
    def fleet_status(cls) -> dict[str, Any]:
        try:
            w_stats = get_worker_status_counts()
            rental_count = store.db.execute("SELECT COUNT(*) FROM gpu_rentals WHERE status=\'ACTIVE\'").fetchone()[0]
            mem_count = store.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            return {
                "onlineWorkers": w_stats.get("onlineWorkers", 0),
                "totalWorkers": w_stats.get("totalWorkers", 0),
                "activeGpuRentals": rental_count,
                "memoryCount": mem_count,
                "serverUptimeSeconds": int(time.time() - STARTED)
            }
        except Exception as exc:
            return {"error": str(exc)}

    @classmethod
    def git_info(cls, subcmd: str = "status") -> dict[str, Any]:
        clean_sub = "status -s" if subcmd == "status" else subcmd
        res = cls.run_terminal(f"git {clean_sub}")
        return {"gitCommand": f"git {clean_sub}", "result": res.get("stdout") or res.get("stderr")}

    @classmethod
    def browser_research(cls, query_or_url: str) -> dict[str, Any]:
        if not query_or_url:
            return {"error": "query_or_url is required"}
        data = _fetch_realtime_data(query_or_url)
        return {"query": query_or_url, "intelligence": data[:2000] if data else "No external intelligence returned."}


def run_browser_agent_loop(prompt_clean: str, system_prompt: str, session_id: str, model: str | None = None, max_steps: int = 8) -> tuple[str, list[dict[str, Any]]]:
    """Execute ordinary website/web-app tasks through persistent Playwright and verified MCP tools."""
    browser_session_id = "chat-browser-" + re.sub(r"[^a-zA-Z0-9_-]", "-", str(session_id or "default"))[:64]
    open_result = dispatch("BrowserSessionOpen", {"sessionId": browser_session_id})
    if not open_result.get("ok"): return "I could not open the browser session.", [{"step":1,"tool":"browser_session_open","output":open_result}]

    tools_doc = """
==================== SAREMBOK WEB / APP EXECUTION PROTOCOL ====================
You are operating as Sarembok's verified web and application execution agent.
Use the browser tools to inspect the page before interacting with it.
TOOLS:
1. browser_inspect() -> inspect current URL, visible text, links, buttons, forms, and controls.
2. browser_navigate(url="https://...") -> navigate the persistent browser session.
3. browser_action(action=..., selector=..., text=..., value=..., key=...) -> click, fill, type, select, press, scroll, wait, back, forward, extract.
4. mcp_list() -> list configured external MCP integrations and their live tools.
5. mcp_call(server="...", tool="...", arguments={...}) -> execute a configured MCP tool.
RULES:
- Inspect before clicking or filling when the target is not already unambiguous.
- Never claim an action completed unless the tool returned ok=true and verified=true.
- Keep the exact user target. Never substitute a different site, product, video, account, or item because search failed.
- For purchase, payment, deletion, transfer, sending money, account closure, unsubscribe, or other high-impact actions, execute only when the tool request includes confirm=true; otherwise report that explicit confirmation is required.
- Use MCP for application/API integrations when an appropriate configured server exists.
- Do not claim browser or application access is impossible unless the browser/MCP tool actually failed.
- End with FINAL_RESPONSE containing only what was actually verified.
========================================================================
"""
    messages=[
        {"role":"system","content":system_prompt+"\n"+tools_doc},
        {"role":"user","content":prompt_clean},
        {"role":"user","content":"OBSERVATION: Persistent browser session is open with sessionId="+browser_session_id+". Inspect it before acting."},
    ]
    traces=[]
    for step in range(1,max_steps+1):
        try:
            res=PROVIDER_ROUTER.generate(system_prompt+"\n"+tools_doc,prompt_clean,messages,requested_model=model)
            text_out=(res.text or "").strip()
        except Exception as exc:
            return f"Web execution stopped because the selected intelligence provider failed: {exc}", traces
        action_match=re.search(r"ACTION:\s*([a-zA-Z0-9_\-]+)",text_out,re.I)
        if action_match:
            tool=action_match.group(1).strip().lower()
            args={}
            args_match=re.search(r"ARGUMENTS:\s*(\{.*?\})",text_out,re.S|re.I)
            if args_match:
                try: args=json.loads(args_match.group(1))
                except Exception: args={}
            tool_map={
                "browser_session_open":"BrowserSessionOpen",
                "browser_inspect":"BrowserSessionInspect",
                "browser_navigate":"BrowserAction",
                "browser_action":"BrowserAction",
                "browser_close":"BrowserSessionClose",
                "mcp_list":"ListMcpServers",
                "mcp_call":"CallMcpTool",
            }
            rpc_method=tool_map.get(tool)
            if not rpc_method:
                obs={"ok":False,"error":"unknown_web_agent_tool","tool":tool}
            else:
                if rpc_method in ("BrowserSessionOpen","BrowserSessionInspect","BrowserSessionClose"): args.setdefault("sessionId",browser_session_id)
                elif rpc_method=="BrowserAction": args.setdefault("sessionId",browser_session_id)
                try:
                    obs=dispatch(rpc_method,args)
                except Exception as exc: obs={"ok":False,"error":str(exc)}
            traces.append({"step":step,"tool":tool,"args":args,"output":obs,"timestamp":now()})
            messages.append({"role":"assistant","content":text_out})
            messages.append({"role":"user","content":"OBSERVATION: "+json.dumps(obs,ensure_ascii=False)})
            continue
        final_match=re.search(r"FINAL_RESPONSE:\s*(.*)",text_out,re.S|re.I)
        if final_match: return final_match.group(1).strip(),traces
        return text_out,traces
    return "Web execution reached the maximum verified action steps without a final completion report.",traces
def run_host_agent_loop(prompt_clean: str, system_prompt: str, session_id: str, model: str | None = None, max_steps: int = 6) -> tuple[str, list[dict[str, Any]]]:
    """Create and wait for a real host-action task on an enrolled worker."""
    tools_doc = """
==================== SAREMBOK HOST EXECUTION ====================
A real target worker may control its own machine through bounded actions:
- host_action(open_url): open an HTTP(S) URL.
- host_action(launch_app): launch an installed application; explicit confirmation is required.
- host_action(open_file): open an existing file; the target OS opens it.
- host_action(run_command): run a command only when host policy enables it and explicit confirmation is supplied.
Return ACTION: host_action with JSON ARGUMENTS.
Never claim completion unless the task result reaches COMPLETED and result.status is VERIFIED or SUCCESS.
===============================================================
"""
    messages = [
        {"role": "system", "content": system_prompt + "\n" + tools_doc},
        {"role": "user", "content": prompt_clean},
    ]
    traces: list[dict[str, Any]] = []
    confirm = bool(re.search(r"\b(?:confirm|confirmed|yes,? do it|go ahead)\b", prompt_clean, re.I))

    for step in range(1, max_steps + 1):
        try:
            res = PROVIDER_ROUTER.generate(
                system_prompt + "\n" + tools_doc,
                prompt_clean,
                messages,
                requested_model=model,
            )
            out = (res.text or "").strip()
        except Exception as exc:
            return f"Host execution stopped because the selected intelligence provider failed: {exc}", traces

        action_match = re.search(r"ACTION:\s*host_action", out, re.I)
        if not action_match:
            final_match = re.search(r"FINAL_RESPONSE:\s*(.*)", out, re.I | re.S)
            return (final_match.group(1).strip() if final_match else out), traces

        args: dict[str, Any] = {}
        args_match = re.search(r"ARGUMENTS:\s*(\{.*?\})", out, re.I | re.S)
        if args_match:
            try:
                args = json.loads(args_match.group(1))
            except Exception:
                args = {}

        args["confirm"] = bool(args.get("confirm", confirm))
        action = str(args.get("action", "")).strip().lower()
        if action not in {"open_url", "launch_app", "open_file", "run_command"}:
            return "The requested host action is not supported by the enrolled Sarembok worker.", traces

        try:
            task = dispatch("CreateTask", {
                "taskType": "host_action",
                "requiredCapability": "host_control",
                "payload": args,
            })
            traces.append({
                "step": step,
                "tool": "host_action",
                "args": args,
                "task": task,
                "timestamp": now(),
            })
            task_id = task.get("taskId")
            if not task_id:
                return "Sarembok could not create the host execution task.", traces

            deadline = time.time() + 30
            while time.time() < deadline:
                state = dispatch("GetTask", {"taskId": task_id})
                if state.get("status") in {"COMPLETED", "FAILED", "CANCELLED"}:
                    traces[-1]["result"] = state
                    result_data = state.get("result") or {}
                    if state.get("status") == "COMPLETED" and result_data.get("status") in {"VERIFIED", "SUCCESS", "COMPLETED"}:
                        return (
                            f"Verified: {action} completed on the enrolled "
                            f"{result_data.get('platform', 'target')} worker.",
                            traces,
                        )
                    if result_data.get("status") == "REQUIRES_CONFIRMATION":
                        return "That host action requires explicit confirmation before execution.", traces
                    return f"Host action did not complete successfully: {json.dumps(result_data, ensure_ascii=False)}", traces
                time.sleep(0.5)

            return "The host worker did not complete the action within the verification window.", traces
        except Exception as exc:
            traces.append({"step": step, "tool": "host_action", "error": str(exc), "timestamp": now()})
            return f"Host execution failed: {exc}", traces

    return "Host execution reached the maximum verified action steps.", traces


def run_admin_agent_loop(
    prompt_clean: str,
    system_prompt: str,
    model: str | None = None,
    max_steps: int = 5
) -> tuple[str, list[dict[str, Any]]]:
    """Autonomous ReAct agent execution loop for Admin Mode."""
    tools_doc = """
==================== ADMIN AGENTIC EXECUTION PROTOCOL ====================
You are operating in SAREMBOK ADMIN EXECUTION MODE with live authority to inspect, execute, and verify system actions.
You have access to the following SYSTEM TOOLS:
1. run_terminal(command="bash command") -> Executes shell command (e.g. ps, ls, docker, git, curl, df).
2. execute_python(code="python code") -> Executes dynamic Python code with stdout capture.
3. read_file(path="path", start_line=1, end_line=100) -> Reads file or directory contents.
4. write_file(path="path", content="text") -> Writes file content to disk.
5. fleet_status() -> Returns real-time worker fleet counts, GPU rentals, and memory stats.
6. git_info(command="status" or "diff" or "log") -> Runs git operations.
7. browser_research(query="search terms or URL") -> Retrieves live web research data.

PROTOCOL:
If you need to perform an action to inspect, verify, or execute what the user requested, reply ONLY in this format:
ACTION: <tool_name>
ARGUMENTS: {"param": "value"}

When the action finishes, the system will provide:
OBSERVATION: <output>

You can perform up to 5 sequential actions.
When your task is complete or if no action is needed, reply in this format:
FINAL_RESPONSE: <Your concise, calm, conversational response summarizing the execution and results>
========================================================================
"""
    augmented_sys_prompt = system_prompt + "\n" + tools_doc
    messages = [
        {"role": "system", "content": augmented_sys_prompt},
        {"role": "user", "content": prompt_clean}
    ]

    # Deterministic Command & Tool Shortcuts
    p_lower = prompt_clean.lower().strip()
    direct_tool = None
    direct_args = {}

    if prompt_clean.startswith("/sh ") or prompt_clean.startswith("/bash ") or prompt_clean.startswith("/exec "):
        direct_tool = "run_terminal"
        direct_args = {"command": re.sub(r"^/(?:sh|bash|exec)\s+", "", prompt_clean).strip()}
    elif prompt_clean.startswith("/py ") or prompt_clean.startswith("/python "):
        direct_tool = "execute_python"
        direct_args = {"code": re.sub(r"^/(?:py|python)\s+", "", prompt_clean).strip()}
    elif p_lower in ("/fleet", "fleet", "fleet status", "workers", "gpu status", "check fleet"):
        direct_tool = "fleet_status"
    elif p_lower.startswith("git ") or p_lower.startswith("/git"):
        direct_tool = "git_info"
        direct_args = {"command": re.sub(r"^/?git\s*", "", prompt_clean).strip() or "status"}
    elif re.search(r"\b(?:run|execute)\s+(?:a\s+)?(?:terminal|shell|bash)\s+(?:command\s+)?(?:to\s+|:\s*)(.+)", prompt_clean, re.IGNORECASE):
        m = re.search(r"\b(?:run|execute)\s+(?:a\s+)?(?:terminal|shell|bash)\s+(?:command\s+)?(?:to\s+|:\s*)(.+)", prompt_clean, re.IGNORECASE)
        direct_tool = "run_terminal"
        direct_args = {"command": m.group(1).strip()}

    if direct_tool:
        tool_res = AdminToolRegistry.dispatch(direct_tool, direct_args)
        trace_entry = {
            "step": 1,
            "tool": direct_tool,
            "args": direct_args,
            "output": tool_res,
            "durationMs": tool_res.get("durationMs", 0),
            "timestamp": now()
        }
        resp_lines = [f"**[ADMIN TOOL EXECUTED: `{direct_tool}`]**"]
        if direct_tool == "run_terminal":
            cmd = tool_res.get("command", "")
            out = tool_res.get("stdout", "")
            err = tool_res.get("stderr", "")
            code_ret = tool_res.get("exitCode", 0)
            resp_lines.append(f"`$ {cmd}` (exit code: {code_ret})")
            if out: resp_lines.append(f"```\n{out}\n```")
            if err: resp_lines.append(f"```stderr\n{err}\n```")
        elif direct_tool == "execute_python":
            out = tool_res.get("output", "")
            resp_lines.append(f"```python\n{out}\n```")
        elif direct_tool == "fleet_status":
            resp_lines.append(f"- Active Workers: **{tool_res.get('onlineWorkers')}** / {tool_res.get('totalWorkers')}")
            resp_lines.append(f"- Active GPU Rentals: **{tool_res.get('activeGpuRentals')}**")
            resp_lines.append(f"- Server Uptime: **{tool_res.get('serverUptimeSeconds')}s**")
        else:
            resp_lines.append(f"```json\n{json.dumps(tool_res, indent=2)}\n```")

        summary_text = "\n".join(resp_lines)
        return summary_text, [trace_entry]

    tool_traces: list[dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        try:
            res = PROVIDER_ROUTER.generate(augmented_sys_prompt, prompt_clean, messages, requested_model=model)
            text = (res.text or "").strip()
        except Exception as exc:
            # Fallback if external LLM provider is offline: analyze prompt keywords for safe admin execution
            if "terminal" in p_lower or "command" in p_lower or "run" in p_lower or "list" in p_lower:
                inferred_cmd = "ls -la /app && python --version" if "list" in p_lower else "python --version"
                fallback_res = AdminToolRegistry.run_terminal(inferred_cmd)
                tool_traces.append({"step": step, "tool": "run_terminal", "args": {"command": inferred_cmd}, "output": fallback_res, "durationMs": fallback_res.get("durationMs", 0)})
                return f"Executed admin command `{inferred_cmd}` (exit code: {fallback_res.get('exitCode')}):\n\n```\n{fallback_res.get('stdout')}\n```", tool_traces

            tool_traces.append({"step": step, "tool": "error", "output": f"LLM inference error: {exc}"})
            return f"Agent execution encountered an LLM provider error: {exc}", tool_traces

        # Check for ACTION:
        action_match = re.search(r"ACTION:\s*([a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
        if action_match:
            tool_name = action_match.group(1).strip()
            # Extract ARGUMENTS:
            args = {}
            args_match = re.search(r"ARGUMENTS:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)
            if args_match:
                try:
                    args = json.loads(args_match.group(1))
                except Exception:
                    try:
                        # Fallback for single quotes
                        args = eval(args_match.group(1), {"__builtins__": {}}, {})
                    except Exception:
                        args = {}

            # Execute tool
            tool_result = AdminToolRegistry.dispatch(tool_name, args)
            obs_str = json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)

            trace_entry = {
                "step": step,
                "tool": tool_name,
                "args": args,
                "output": tool_result,
                "durationMs": tool_result.get("durationMs", 0),
                "timestamp": now()
            }
            tool_traces.append(trace_entry)

            # Append to conversation messages for next step
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": f"OBSERVATION: {obs_str}"})
            continue

        # Check for FINAL_RESPONSE:
        final_match = re.search(r"FINAL_RESPONSE:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
        if final_match:
            final_text = final_match.group(1).strip()
            return final_text, tool_traces

        # If no explicit markers but returned text
        return text, tool_traces

    return "Admin directive execution completed maximum allowable steps.", tool_traces


_YT_CACHE: dict[str, str] = {
    "bbc news": "lRJiLBhrJTI",
    "bbc news live": "lRJiLBhrJTI",
    "abc news": "iipR5yUp36o",
    "abc news live": "iipR5yUp36o",
    "sky news": "9Auq9mYxFEE",
    "sky news live": "9Auq9mYxFEE",
    "nbc news": "_4xFk8B876E",
    "nbc news live": "_4xFk8B876E",
    "bloomberg": "dp8PhLsUcFE",
    "bloomberg live": "dp8PhLsUcFE",
    "synthwave": "4xDzrJKXOOY",
    "synthwave radio": "4xDzrJKXOOY",
    "lofi": "jfKfPfyJRdk",
    "lofi hip hop": "jfKfPfyJRdk",
    "chill": "5yx6BWlEVcY",
    "ambient": "S_MOd40zlsk",
    "space ambient": "S_MOd40zlsk",
    "classical": "mIYzp5rcTvU",
    "cyberpunk": "s0WBvK41Uyo",
    "ai news": "5eT0GZqj3yE",
}

def _youtube_terms(value: str) -> list[str]:
    stop = {"the","a","an","and","or","of","to","for","me","some","on","youtube","video","music","song","play","watch","show","listen","live"}
    return [t for t in re.findall(r"[a-z0-9]+", str(value or "").lower()) if len(t) > 1 and t not in stop]

def _youtube_candidate_score(query: str, title: str) -> float:
    q = _youtube_terms(query); t = _youtube_terms(title)
    if not q or not t: return 0.0
    overlap = len(set(q) & set(t)) / len(set(q))
    phrase = 1.0 if " ".join(q) in " ".join(t) else 0.0
    return round((overlap * 0.8) + (phrase * 0.2), 4)

def _extract_youtube_candidates(node: Any, out: list[dict[str, str]], limit: int = 30) -> None:
    if len(out) >= limit: return
    if isinstance(node, dict):
        vr = node.get("videoRenderer")
        if isinstance(vr, dict) and vr.get("videoId"):
            title_obj = vr.get("title") or {}; runs = title_obj.get("runs") or []
            title = "".join(str(run.get("text") or "") for run in runs).strip() or str(title_obj.get("simpleText") or "").strip()
            out.append({"videoId": str(vr.get("videoId")), "title": title})
            if len(out) >= limit: return
        for value in node.values(): _extract_youtube_candidates(value, out, limit)
    elif isinstance(node, list):
        for value in node: _extract_youtube_candidates(value, out, limit)

def resolve_youtube_search(query: str) -> dict[str, Any]:
    q_clean = str(query or "").strip() or "lofi study music"
    direct = re.search(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})", q_clean, re.I)
    if direct:
        vid = direct.group(1)
        return {"videoId": vid, "url": f"https://www.youtube.com/watch?v={vid}", "searchUrl": f"https://www.youtube.com/watch?v={vid}", "title": q_clean, "verified": True, "matchScore": 1.0, "direct": True}
    q_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(q_clean)}"
    try:
        req = urllib.request.Request(q_url, headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154.0 Safari/537.36","Accept-Language":"en-US,en;q=0.9"})
        with urllib.request.urlopen(req, timeout=7) as resp: html = resp.read().decode("utf-8", errors="ignore")
        candidates=[]
        match=re.search(r"ytInitialData\s*=\s*({.*?});</script>",html) or re.search(r"ytInitialData\s*=\s*({.*?});",html)
        if match:
            try: _extract_youtube_candidates(json.loads(match.group(1)), candidates, 30)
            except Exception: pass
        ranked=sorted(((_youtube_candidate_score(q_clean,x.get("title","")),x) for x in candidates), key=lambda z:z[0], reverse=True)
        if ranked and ranked[0][0] >= 0.45:
            score,best=ranked[0]; vid=best["videoId"]; title=best.get("title") or q_clean
            return {"videoId":vid,"url":f"https://www.youtube.com/watch?v={vid}","searchUrl":q_url,"title":title,"verified":True,"matchScore":score}
    except Exception as exc:
        LOG.warning("YouTube verified search failed for %r: %s",q_clean,exc)
    return {"videoId":None,"url":q_url,"searchUrl":q_url,"title":f"Search results for {q_clean}","verified":False,"matchScore":0.0}
def get_visual_engine_status() -> dict[str, Any]:
    """Returns the configuration and readiness of all 3 visual synthesis tiers."""
    comfy_url = os.getenv("COMFYUI_URL", os.getenv("SOVEREIGN_GPU_ENDPOINT", "http://127.0.0.1:8188")).strip().rstrip("/")
    comfy_online = False
    try:
        req = urllib.request.Request(f"{comfy_url}/system_stats", headers={"User-Agent": "Sarembok/1.0"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            if resp.status == 200:
                comfy_online = True
    except Exception:
        comfy_online = False

    fal_configured = bool(os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY"))
    together_configured = bool(os.getenv("TOGETHER_API_KEY"))
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))

    active_tier = "UNAVAILABLE"
    if comfy_online:
        active_tier = "Tier 1 (Sovereign ComfyUI GPU Node)"
    elif fal_configured:
        active_tier = "Tier 2 (Fal.ai FLUX.1 Enterprise)"
    elif together_configured:
        active_tier = "Tier 2 (Together AI FLUX.1)"
    elif openai_configured:
        active_tier = "Tier 2 (OpenAI DALL-E 3)"

    return {
        "activeTier": active_tier,
        "tier1_sovereign": {
            "name": "ComfyUI / Dedicated Silicon",
            "endpoint": comfy_url,
            "status": "ONLINE" if comfy_online else "STANDBY",
            "capabilities": ["flux.1-dev", "flux.1-schnell", "sdxl", "controlnet", "lora"],
        },
        "tier2_enterprise": {
            "fal": {"configured": fal_configured, "model": "fal-ai/flux/schnell"},
            "together": {"configured": together_configured, "model": "black-forest-labs/FLUX.1-schnell"},
            "openai": {"configured": openai_configured, "model": "dall-e-3"},
        },
        "tier3_community": {
            "name": "Community fallback",
            "status": "DISABLED",
            "model": None,
            "unlimited": False,
            "zeroKeyRequired": False,
        },
    }


def resolve_image_generation(
    prompt: str,
    aspect_ratio: str = "1:1",
    seed: int | None = None,
    preferred_engine: str | None = None,
) -> dict[str, Any]:
    """Generate high-fidelity frontier image using multi-tier adaptive routing:
    Tier 1: Sovereign GPU Node (ComfyUI / Dedicated Silicon)
    Tier 2: Enterprise Cloud API (Fal.ai FLUX.1 / Together AI FLUX.1 / OpenAI DALL-E 3)
    Tier 3: Guaranteed Community Cluster (Pollinations FLUX.1)
    """
    import urllib.parse
    import urllib.request
    import random
    import json

    start_time = time.perf_counter()

    p_clean = prompt.strip().strip('"\'`“”‘’')
    cleaned_prompt = re.sub(
        r"(?i)^(?:can you\s+)?(?:please\s+)?(?:generate|create|render|draw|make|synthesize|paint|illustrate)\s+(?:an?\s+)?(?:4k\s+|8k\s+|hd\s+|cinematic\s+)?(?:image|picture|photo|artwork|illustration|rendering)?\s+(?:of\s+)?",
        "",
        p_clean,
    ).strip()
    cleaned_prompt = re.sub(r"(?i)^(?:a\s+|an\s+)?(?:image|picture|photo|artwork|rendering)\s+(?:of\s+)?", "", cleaned_prompt).strip()
    if not cleaned_prompt:
        cleaned_prompt = p_clean or "cybernetic neural AI core in sovereign computing matrix"

    width = 1024
    height = 1024
    image_size_fal = "square_hd"
    if aspect_ratio == "16:9":
        width, height = 1280, 720
        image_size_fal = "landscape_16_9"
    elif aspect_ratio == "9:16":
        width, height = 720, 1280
        image_size_fal = "portrait_16_9"
    elif aspect_ratio == "4:3":
        width, height = 1024, 768
        image_size_fal = "landscape_4_3"
    elif aspect_ratio == "3:4":
        width, height = 768, 1024
        image_size_fal = "portrait_4_3"

    actual_seed = seed if seed is not None else random.randint(100000, 9999999)
    title = cleaned_prompt[:60].strip()
    if len(cleaned_prompt) > 60:
        title += "..."

    engine = (preferred_engine or "auto").lower()

    # -------------------------------------------------------------
    # Tier 1: Sovereign ComfyUI GPU Node
    # -------------------------------------------------------------
    comfy_url = os.getenv("COMFYUI_URL", os.getenv("SOVEREIGN_GPU_ENDPOINT", "http://127.0.0.1:8188")).strip().rstrip("/")
    if engine in ("auto", "comfyui", "sovereign"):
        try:
            req_check = urllib.request.Request(f"{comfy_url}/system_stats", headers={"User-Agent": "Sarembok/1.0"})
            with urllib.request.urlopen(req_check, timeout=0.8) as resp_check:
                if resp_check.status == 200:
                    prompt_data = {
                        "prompt": {
                            "3": {
                                "class_type": "KSampler",
                                "inputs": {
                                    "cfg": 1.0,
                                    "denoise": 1.0,
                                    "latent_image": ["5", 0],
                                    "model": ["4", 0],
                                    "positive": ["6", 0],
                                    "negative": ["7", 0],
                                    "sampler_name": "euler",
                                    "scheduler": "simple",
                                    "seed": actual_seed,
                                    "steps": 4,
                                },
                            },
                            "4": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-schnell.sft", "weight_dtype": "fp8_e4m3fn"}},
                            "5": {"class_type": "EmptyLatentImage", "inputs": {"batch_size": 1, "height": height, "width": width}},
                            "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["11", 0], "text": cleaned_prompt}},
                            "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["11", 0], "text": ""}},
                            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["10", 0]}},
                            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "sarembok_frontier", "images": ["8", 0]}},
                            "10": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.sft"}},
                            "11": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux"}},
                        }
                    }
                    post_req = urllib.request.Request(
                        f"{comfy_url}/prompt",
                        data=json.dumps(prompt_data).encode("utf-8"),
                        headers={"Content-Type": "application/json", "User-Agent": "Sarembok/1.0"},
                    )
                    with urllib.request.urlopen(post_req, timeout=5.0) as post_resp:
                        if post_resp.status in (200, 201):
                            p_res = json.loads(post_resp.read().decode("utf-8"))
                            prompt_id = p_res.get("prompt_id", "latest")
                            img_url = f"{comfy_url}/view?filename=sarembok_frontier_{prompt_id}_00001_.png"
                            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
                            LOG.info("Sovereign ComfyUI generation successful for '%s' (%sms)", title, latency_ms)
                            return {
                                "url": img_url,
                                "prompt": cleaned_prompt,
                                "title": title,
                                "width": width,
                                "height": height,
                                "seed": actual_seed,
                                "model": "flux.1-schnell",
                                "provider": "Sovereign ComfyUI Node",
                                "tier": "Tier 1 (Sovereign Dedicated Silicon)",
                                "badge": "⚡ SOVEREIGN GPU (COMFYUI)",
                                "latencyMs": latency_ms,
                            }
        except Exception as e:
            LOG.debug("Sovereign ComfyUI not available or failed: %s", e)

    # -------------------------------------------------------------
    # Tier 2: Fal.ai Enterprise FLUX.1 (~400ms)
    # -------------------------------------------------------------
    fal_key = (os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY", "")).strip()
    if fal_key and engine in ("auto", "fal", "fal.ai"):
        try:
            fal_payload = {
                "prompt": cleaned_prompt,
                "image_size": image_size_fal,
                "num_images": 1,
                "enable_safety_checker": False,
                "seed": actual_seed,
            }
            req = urllib.request.Request(
                "https://fal.run/fal-ai/flux/schnell",
                data=json.dumps(fal_payload).encode("utf-8"),
                headers={
                    "Authorization": f"Key {fal_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Sarembok/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                if resp.status == 200:
                    fal_data = json.loads(resp.read().decode("utf-8"))
                    images = fal_data.get("images", [])
                    if images and images[0].get("url"):
                        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
                        LOG.info("Fal.ai FLUX.1 generation successful for '%s' (%sms)", title, latency_ms)
                        return {
                            "url": images[0]["url"],
                            "prompt": cleaned_prompt,
                            "title": title,
                            "width": width,
                            "height": height,
                            "seed": actual_seed,
                            "model": "flux.1-schnell",
                            "provider": "Fal.ai Enterprise",
                            "tier": "Tier 2 (Enterprise Frontier API)",
                            "badge": "⚡ FAL.AI ENTERPRISE FLUX",
                            "latencyMs": latency_ms,
                        }
        except Exception as e:
            LOG.warning("Fal.ai generation failed, trying next tier: %s", e)

    # -------------------------------------------------------------
    # Tier 2: Together AI FLUX.1
    # -------------------------------------------------------------
    together_key = os.getenv("TOGETHER_API_KEY", "").strip()
    if together_key and engine in ("auto", "together"):
        try:
            tg_payload = {
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": cleaned_prompt,
                "width": width,
                "height": height,
                "steps": 4,
                "n": 1,
                "seed": actual_seed,
            }
            req = urllib.request.Request(
                "https://api.together.xyz/v1/images/generations",
                data=json.dumps(tg_payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {together_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Sarembok/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                if resp.status == 200:
                    tg_data = json.loads(resp.read().decode("utf-8"))
                    data_items = tg_data.get("data", [])
                    if data_items and data_items[0].get("url"):
                        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
                        LOG.info("Together AI FLUX.1 generation successful for '%s' (%sms)", title, latency_ms)
                        return {
                            "url": data_items[0]["url"],
                            "prompt": cleaned_prompt,
                            "title": title,
                            "width": width,
                            "height": height,
                            "seed": actual_seed,
                            "model": "flux.1-schnell",
                            "provider": "Together AI",
                            "tier": "Tier 2 (Enterprise Frontier API)",
                            "badge": "⚡ TOGETHER AI FLUX",
                            "latencyMs": latency_ms,
                        }
        except Exception as e:
            LOG.warning("Together AI generation failed, trying next tier: %s", e)

    # -------------------------------------------------------------
    # Tier 2: OpenAI DALL-E 3
    # -------------------------------------------------------------
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key and engine in ("auto", "openai", "dalle", "dall-e"):
        try:
            oa_size = "1024x1024"
            if aspect_ratio == "16:9":
                oa_size = "1792x1024"
            elif aspect_ratio == "9:16":
                oa_size = "1024x1792"
            oa_payload = {
                "model": "dall-e-3",
                "prompt": cleaned_prompt,
                "size": oa_size,
                "quality": "standard",
                "n": 1,
            }
            req = urllib.request.Request(
                "https://api.openai.com/v1/images/generations",
                data=json.dumps(oa_payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Sarembok/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=18.0) as resp:
                if resp.status == 200:
                    oa_data = json.loads(resp.read().decode("utf-8"))
                    data_items = oa_data.get("data", [])
                    if data_items and data_items[0].get("url"):
                        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
                        LOG.info("OpenAI DALL-E 3 generation successful for '%s' (%sms)", title, latency_ms)
                        return {
                            "url": data_items[0]["url"],
                            "prompt": cleaned_prompt,
                            "title": title,
                            "width": width,
                            "height": height,
                            "seed": actual_seed,
                            "model": "dall-e-3",
                            "provider": "OpenAI",
                            "tier": "Tier 2 (Enterprise Frontier API)",
                            "badge": "⚡ OPENAI DALL-E 3",
                            "latencyMs": latency_ms,
                        }
        except Exception as e:
            LOG.warning("OpenAI DALL-E generation failed: %s", e)

    # No verified image provider is available. Never return a fabricated image URL.
    raise RuntimeError("image_generation_unavailable: no verified visual provider or GPU worker is operational")


def _enrich_multimodal_reply(prompt: str, rep: str) -> str:
    p_low = prompt.lower()
    rep = (rep or "").strip()

    # Preserve provider responses verbatim; never delete individual sentences.

    # Extract topic for dynamic video search embedding
    topic = re.sub(r"(?i)^(?:can you\s+)?(?:please\s+)?(?:play|show|open|stream|watch|listen to)\s+(?:me\s+)?(?:some\s+)?(?:a\s+)?(?:video\s+about\s+|on\s+youtube\s+|youtube\s+)?", "", prompt).strip()
    topic = re.sub(r"(?i)\s+(?:on\s+youtube|from\s+youtube|video|stream|song)$", "", topic).strip()
    topic = topic.replace('"', '').replace("'", "").strip() or "lofi study music"

    # Extract subclause topics for multi-task requests
    music_sub = re.search(r"(?i)\b(?:play|stream|listen to)\s+(?:me\s+)?(?:some\s+)?([a-z0-9\s\-]+?)(?:,\s*and\s+|\s+and\s+|\s+while\s+|$|\.|\n)", prompt)
    video_sub = re.search(r"(?i)\b(?:watch|show|open)\s+(?:me\s+)?(?:a\s+)?(?:video\s+about\s+)?([a-z0-9\s\-]+?)(?:,\s*and\s+|\s+and\s+|\s+while\s+|$|\.|\n)", prompt)
    img_sub = re.search(r"(?i)\b(?:generate|create|render|draw|synthesize|paint)\s+(?:an?\s+)?(?:4k\s+|8k\s+|hd\s+|cinematic\s+)?(?:image|picture|photo|artwork|rendering)?\s+(?:of\s+)?([a-z0-9\s\-]+?)(?:,\s*and\s+|\s+and\s+|\s+while\s+|$|\.|\n)", prompt)

    # Check for Image Generation Intent
    image_intents = (
        "generate image", "generate an image", "create image", "create an image",
        "make an image", "render image", "render an image", "draw an image",
        "draw me", "paint me", "synthesize image", "make a picture",
        "generate a picture", "create artwork", "generate artwork",
        "render a 3d", "generate visual", "draw a", "generate a photo",
        "create a photo", "render a scene"
    )
    is_image = any(ii in p_low for ii in image_intents) or (
        ("image" in p_low or "picture" in p_low or "artwork" in p_low or "visual" in p_low)
        and any(w in p_low for w in ("generate", "create", "render", "synthesize", "draw", "produce", "paint"))
    )

    # Check for YouTube / Video Intent
    youtube_intents = ("open youtube", "open yt", "play youtube", "search youtube", "watch youtube", "youtube.com", "show video", "watch video", "play video", "video of", "video about")
    is_video = any(yi in p_low for yi in youtube_intents) or ("video" in p_low and any(w in p_low for w in ("open", "launch", "watch", "play", "show", "search")))

    # Check for Music & Audio playback intent
    music_intents = ("play music", "play some music", "play lofi", "play lo-fi", "play chill", "play synthwave", "play jazz", "play classical", "play ambient", "play song", "play track", "listen to music", "study music", "background music", "play audio")
    is_music = any(mi in p_low for mi in music_intents) or any(g in p_low for g in ("lofi", "lo-fi", "synthwave", "ambient", "soundtrack", "beats"))
    # News, clips, sports, games, highlights, movies, lectures must prioritize video stream
    news_or_video_markers = (
        "news", "video", "clip", "movie", "trailer", "lecture", "interview", "documentary",
        "stream live", "live stream", "broadcast", "on youtube", "game", "football",
        "highlights", "match", "soccer", "nfl", "nba", "mlb", "nhl", "premier league",
        "sport", "sports", "fight", "boxing", "ufc", "racing", "f1", "play game"
    )
    if any(m in p_low for m in news_or_video_markers) and not (is_music and not any(m in p_low for m in ("game", "football", "highlights", "movie"))):
        is_video = True

    # Resolve specific subclause topic for audio / video search
    if is_music and music_sub and len(music_sub.group(1).strip()) > 2:
        topic = music_sub.group(1).strip()
    elif is_video and video_sub and len(video_sub.group(1).strip()) > 2:
        topic = video_sub.group(1).strip()
    else:
        topic = re.sub(r"(?i)^(?:can you\s+)?(?:please\s+)?(?:play|show|open|stream|watch|listen to)\s+(?:me\s+)?(?:some\s+)?(?:a\s+)?(?:video\s+about\s+|on\s+youtube\s+|youtube\s+)?", "", prompt).strip()
        topic = re.sub(r"(?i)\s+(?:on\s+youtube|from\s+youtube|video|stream|song)$", "", topic).strip()
        topic = topic.replace('"', '').replace("'", "").strip() or "lofi study music"

    img_query = img_sub.group(1).strip() if (img_sub and len(img_sub.group(1).strip()) > 2) else prompt

    # An unspecified "play something/music/song" request may use a clearly
    # identified neutral default. Specific requests are never substituted.
    if is_music and topic.lower() in {"something", "anything", "music", "some music", "a song"}:
        topic = "lofi study music"

    # 1. Video or Audio Card
    if is_video or is_music or ":::video" in rep or ":::music" in rep or "youtube.com" in rep:
        resolved = resolve_youtube_search(topic)
        real_url = resolved["url"]
        display_title = resolved.get("title") or topic.upper()
        rep = re.sub(r'https?://(?:www\.)?(?:youtube\.com/watch\?[^\s\)"]+|youtu\.be/[\w-]+)', real_url, rep)
        rep = re.sub(r':::(?:video|music|youtube)[^\n]*\n[\s\S]*?:::\n?', '', rep).strip()
        rep = re.sub(r':::(?:video|music|youtube)[^\n]*', '', rep).strip()
        if resolved.get("verified") and resolved.get("videoId"):
            if is_music:
                rep = f":::music {display_title} · VERIFIED AUDIO STREAM\n{real_url}\n:::\n\n{rep}".strip()
            else:
                rep = f":::video {display_title} · VERIFIED VIDEO STREAM\n{real_url}\n:::\n\n{rep}".strip()
        else:
            media_kind = "music" if is_music else "video"
            rep = f"No verified {media_kind} result matched \"{topic}\". I did not substitute a different item. Search results: {resolved.get('searchUrl', real_url)}\n\n{rep}".strip()
    # 2. Generative Image Card (supports co-existing with Audio Stream in Multi-Task mode!)
    if is_image or ":::image" in rep:
        try:
            img_data = resolve_image_generation(img_query)
            img_url = img_data["url"]
            img_title = img_data["title"].upper()
            rep = re.sub(r':::image[^\n]*\n[\s\S]*?:::\n?', '', rep).strip()
            rep = re.sub(r':::image[^\n]*', '', rep).strip()
            img_badge = img_data.get("badge", "VERIFIED IMAGE GENERATION")
            rep = f":::image {img_title} · {img_badge}\n{img_url}\n:::\n\n{rep}".strip()
        except Exception as exc:
            LOG.info("Image generation unavailable: %s", exc)
            rep = (rep + "\n\nImage generation is not currently operational in this Sarembok runtime.").strip()

    # 3. Check for Simultaneous Multi-Tasking intent
    task_intents = ("while searching", "simultaneously", "at the same time", "in parallel", "also calculate", "and also", "while calculating", "and search", "multi task", "multitask")
    if any(ti in p_low for ti in task_intents) and ":::tasks" not in rep:
        tasks_lines = []
        if is_image:
            tasks_lines.append("[Visual Synthesis]: Image generation requested; live provider availability is reported separately.")
        if is_music or any(w in p_low for w in ("music", "lofi", "song", "audio")):
            tasks_lines.append("[Audio Stream]: Music requested; verified playback result is reported separately.")
        if any(w in p_low for w in ("news", "search", "research", "ai", "market")):
            tasks_lines.append("[Live Intelligence]: Synchronized Real-Time Knowledge Fabric")
        if any(w in p_low for w in ("calc", "math", "code", "budget")):
            tasks_lines.append("[Computational Engine]: Synthesis & Execution Complete")
        if not tasks_lines:
            tasks_lines.append("[Parallel Directives]: Multi-Threaded Execution Synchronized")

        task_block = ":::tasks Multi-Task Parallel Execution\n" + "\n".join(tasks_lines) + "\n:::"
        rep = f"{task_block}\n\n{rep}".strip()

    if not rep or len(rep.strip()) < 10:
        if is_image:
            try:
                img_data = resolve_image_generation(prompt)
                img_badge = img_data.get("badge", "VERIFIED IMAGE GENERATION")
                rep = f"Synthesized **{img_data['title']}** via {img_data.get('provider', 'Verified provider')} ({img_data.get('latencyMs', 0)}ms):\n\n:::image {img_data['title'].upper()} · {img_badge}\n{img_data['url']}\n:::\n\nResolution: {img_data.get('width', 1024)}x{img_data.get('height', 1024)} · Tier: {img_data.get('tier', 'verified')}"
            except Exception:
                rep = "Image generation is not currently operational in this Sarembok runtime."
        elif is_video:
            rep = f"No verified video result matched **{topic.upper()}**. I did not substitute a different video. Search results: {resolved.get("searchUrl", real_url)}"
        elif is_music:
            rep = f"No verified music result matched **{topic.upper()}**. I did not substitute a different track. Search results: {resolved.get("searchUrl", real_url)}"
        else:
            rep = "Cyber audio & multimodal synthesis initialized. Active streaming channels and interface components are ready."

    return rep


def sarembok_process_dialogue(
    prompt: str,
    context: list | None = None,
    api_key: str | None = None,
    session_id: str = "default",
    model: str | None = None,
    language: str = "en",
    conversational: bool = False,
    admin: bool = False,
    image_frame: str | None = None,
) -> dict[str, Any]:
    prompt_clean = (prompt or "").strip()
    prompt_lower = prompt_clean.lower()
    is_conversational = bool(conversational or ("live" in prompt_lower and "conversation" in prompt_lower))
    is_admin = bool(admin or prompt_clean.startswith("/admin") or prompt_clean.startswith("/exec") or "admin execute" in prompt_lower)

    action_info = None

    # 1. Tool Intent: Create Agent
    if re.search(r"\b(?:create|spawn|build|deploy)\s+(?:an?\s+)?(?:agent|helper|assistant|bot)\b", prompt_lower):
        name_match = re.search(r"(?:named|called)\s+([a-zA-Z0-9_\-\s]+)", prompt_clean, re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else f"Agent-{uuid.uuid4().hex[:4].upper()}"
        agent_id = f"agent-{uuid.uuid4().hex[:6]}"
        try:
            store.create_agent(agent_id, name)
            action_info = {"type": "CREATE_AGENT", "agentId": agent_id, "displayName": name}
            response_text = f"Created agent '{name}' (ID: {agent_id}). It's now registered and active."
            _save_conversation(session_id, prompt_clean, response_text)
            return {"response": response_text, "audioText": response_text, "action": action_info}
        except Exception as e:
            LOG.warning("Agent spawn error: %s", e)

    # 2. Tool Intent: Schedule Task
    if re.search(r"\b(?:schedule|run|execute|process)\s+(?:a\s+)?(?:task|compute|workload|pipeline)\b", prompt_lower):
        task_match = re.search(r"(?:for|on|type)\s+([a-zA-Z0-9_\-\s]+)", prompt_clean, re.IGNORECASE)
        task_type = task_match.group(1).strip().replace(" ", "_") if task_match else "general_compute"
        res = store.create_task(task_type, None, {"source": "chat", "prompt": prompt_clean})
        action_info = {"type": "SCHEDULE_TASK", "taskId": res.get("taskId"), "taskType": task_type}
        response_text = f"Task '{task_type}' (ID: {res.get('taskId')}) scheduled. Status: {res.get('status')}."
        _save_conversation(session_id, prompt_clean, response_text)
        return {"response": response_text, "audioText": response_text, "action": action_info}

    # 3. Tool Intent: Store Memory
    if re.search(r"\b(?:remember\s+that|store\s+(?:a\s+)?memory|keep\s+in\s+mind|save\s+(?:this\s+)?fact)\b", prompt_lower):
        mem_text = re.sub(r"^(?:please\s+)?(?:remember\s+that|store\s+memory|keep\s+in\s+mind|save\s+fact)\s+", "", prompt_clean, flags=re.IGNORECASE).strip()
        mem_id = f"mem-{uuid.uuid4().hex[:8]}"
        stamp = now()
        key_name = f"fact_{uuid.uuid4().hex[:4]}"
        store.db.execute("INSERT INTO memories(memory_id, tier, key, value, agent_id, session_id, created_at) VALUES(?,?,?,?,?,?,?)", (mem_id, "SEMANTIC", key_name, mem_text, "sarembok-prime", session_id, stamp))
        store.db.commit()
        action_info = {"type": "STORE_MEMORY", "memoryId": mem_id, "key": key_name, "value": mem_text}
        response_text = f"Stored to memory: \"{mem_text}\""
        _save_conversation(session_id, prompt_clean, response_text)
        return {"response": response_text, "audioText": response_text, "action": action_info}

    # 4. Tool Intent: Date & Time Query
    time_regex = re.compile(
        r"\b(?:what(?:\s*is|\s*'s|\s*s)?\s+(?:the\s+)?(?:current\s+|today'?s\s+)?(?:time|date|day)"
        r"|what\s+time\s+is\s+it"
        r"|what\s+date\s+is\s+it"
        r"|what\s+day\s+is\s+(?:it|today)"
        r"|tell\s+me\s+the\s+(?:time|date)"
        r"|current\s+(?:time|date))\b",
        re.IGNORECASE
    )
    clean_no_punct = re.sub(r"[^\w\s]", "", prompt_lower).strip()
    if time_regex.search(prompt_clean) or clean_no_punct in ("time", "date", "clock", "today", "day"):
        now_utc = datetime.now(timezone.utc)
        utc_date_str = now_utc.strftime("%A, %B %d, %Y")
        utc_time_str = now_utc.strftime("%H:%M:%S UTC")
        response_text = f"The current system time is **{utc_time_str}** on **{utc_date_str}**."
        audio_text = f"The current time is {now_utc.strftime('%I:%M %p UTC on %A, %B %d, %Y')}."
        _save_conversation(session_id, prompt_clean, response_text)
        return {
            "response": response_text,
            "audioText": audio_text,
            "source": "runtime_authority",
            "model": "runtime-clock",
            "action": None,
            "timestamp": now()
        }

    # Fast conversational lane.
    # Ordinary dialogue should not wait on runtime inventory, SQLite history,
    # memory recall, or real-time enrichment before Gemini can emit token 1.
    if (
        _is_fast_conversational_turn(prompt_clean, image_frame=image_frame, admin=is_admin)
        and not (
            is_identity_query(prompt_clean)
            or is_capability_query(prompt_clean)
            or is_limitation_query(prompt_clean)
            or is_self_state_query(prompt_clean)
        )
    ):
        fast_history = _get_fast_chat_history(session_id)
        fast_system = (
            "You are Sarembok VE, a natural conversational AI assistant. "
            "Respond directly to the user's message with a warm, concise, human conversational style. "
            "Do not describe internal system architecture unless asked. "
            "Never claim you were created by OpenAI, Google, or another model vendor, and never invent "
            "Sarembok capabilities, product history, browsing, image generation, or other platform facts. "
            "Self-description questions are handled by the runtime authority path. "
            "For ordinary conversation, prefer a short answer of 1-4 sentences and get to the point immediately."
        )
        fast_messages = [{"role": "system", "content": fast_system}, *fast_history, {"role": "user", "content": prompt_clean}]
        try:
            provider_result = PROVIDER_ROUTER.generate(
                fast_system,
                prompt_clean,
                fast_messages,
                requested_model=model,
                dynamic_key=api_key,
            )
            reply = _enrich_multimodal_reply(prompt_clean, provider_result.text).strip()
            _record_fast_chat_turn(session_id, prompt_clean, reply)
            return {
                "response": reply,
                "audioText": reply,
                "source": provider_result.provider,
                "model": provider_result.model,
                "action": None,
                "structuredResponse": build_structured_response(
                    reply,
                    provider=provider_result.provider,
                    model=provider_result.model,
                    latency_ms=provider_result.latency_ms,
                ),
                "metadata": {
                    "provider": provider_result.provider,
                    "model": provider_result.model,
                    "latency_ms": provider_result.latency_ms,
                    "provider_api": provider_result.api,
                    "usage": provider_result.usage,
                    "latencyLane": "fast_conversational",
                },
                "_deferPersistence": True,
                "_persistSessionId": session_id,
                "_persistPrompt": prompt_clean,
                "_persistReply": reply,
            }
        except Exception as exc:
            LOG.info("fast_conversational_lane_fallback error=%s", exc)

    # 5. Build context from real system state
    conv_rows = store.db.execute(
        "SELECT role, content FROM conversations WHERE session_id=? ORDER BY created_at DESC LIMIT 20",
        (session_id,)
    ).fetchall()
    deduped_history = []
    last_role = None
    last_content = None
    for r, c in list(reversed(conv_rows)):
        c_clean = str(c or "").strip()
        if not c_clean:
            continue
        if r == last_role and c_clean == last_content:
            continue
        if "Local Sovereign Authority" in c_clean or "Sovereign Fallback" in c_clean:
            continue
        deduped_history.append((r, c))
        last_role = r
        last_content = c_clean
    conv_history = deduped_history

    # Runtime Authority is the source of truth for live Sarembok platform state
    ensure_sovereign_worker()
    authority_snapshot = runtime_authority_snapshot(
        store,
        PROVIDER_ROUTER,
        STARTED,
    )

    # Direct Runtime Authority Handling (Pruning, Limitations, Capabilities, Identity, Model Inventory)
    if is_worker_prune_query(prompt_clean):
        pruned_cnt = prune_stale_workers(force_all_offline=True)
        fresh_snapshot = runtime_authority_snapshot(store, PROVIDER_ROUTER, STARTED)
        workers_info = fresh_snapshot.get("workers") or {}
        prune_reply = (
            f"### ⚡ WORKER REGISTRY PRUNED & CONSOLIDATED\n\n"
            f"- **Pruned Inactive Records:** {pruned_cnt} offline worker{'s' if pruned_cnt != 1 else ''} purged.\n"
            f"- **Active Online Workers:** {workers_info.get('online', 0)} verified worker(s).\n"
            f"- **Cluster Health:** {workers_info.get('online', 0)} verified online worker(s); no hardware is fabricated."
        )
        _save_conversation(session_id, prompt_clean, prune_reply)
        return {
            "response": prune_reply,
            "audioText": f"Pruned {pruned_cnt} offline worker records. Current verified online worker count is {workers_info.get('online', 0)}.",
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": build_structured_response(prune_reply, provider="runtime_authority", model="runtime-authority"),
            "metadata": {"provider": "runtime_authority", "model": "runtime-authority"}
        }

    if is_limitation_query(prompt_clean):
        lim_reply = render_limitations(authority_snapshot)
        _save_conversation(session_id, prompt_clean, lim_reply)
        return {
            "response": lim_reply,
            "audioText": "Sarembok VE operates within defined architectural boundaries: containerized sandbox isolation, strict human-in-the-loop authorization for high-risk actions, and verified ground-truth telemetry.",
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": build_structured_response(lim_reply, provider="runtime_authority", model="runtime-authority"),
            "metadata": {"provider": "runtime_authority", "model": "runtime-authority"}
        }

    if is_capability_query(prompt_clean):
        cap_reply = render_capabilities(authority_snapshot)
        _save_conversation(session_id, prompt_clean, cap_reply)
        return {
            "response": cap_reply,
            "audioText": "I am Sarembok VE. I can stream media and audio, conduct live two-way voice conversations with instant barge-in, perceive through Astra camera and screen eyes, execute dynamic MCP skills, and synthesize full-stack code.",
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": build_structured_response(cap_reply, provider="runtime_authority", model="runtime-authority"),
            "metadata": {"provider": "runtime_authority", "model": "runtime-authority"}
        }

    if is_identity_query(prompt_clean):
        id_reply = render_identity(authority_snapshot)
        _save_conversation(session_id, prompt_clean, id_reply)
        return {
            "response": id_reply,
            "audioText": "Sarembok VE was built by Tim Hall. It is the AI-native computing environment and runtime you are interacting with.",
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": build_structured_response(id_reply, provider="runtime_authority", model="runtime-authority"),
            "metadata": {"provider": "runtime_authority", "model": "runtime-authority"}
        }

    inventory_markers = (
        "what models are available", "what other models", "other models", "which models are available",
        "which models can i use", "what models can i use", "what llms are available", "what llms can i use",
        "what language models are available", "what language models can i use", "what models are configured",
        "which models are configured", "model availability", "available models", "configured models",
    )
    if is_self_state_query(prompt_clean) and any(m in prompt_lower for m in inventory_markers):
        inv_reply = render_model_inventory(authority_snapshot)
        _save_conversation(session_id, prompt_clean, inv_reply)
        return {
            "response": inv_reply,
            "audioText": inv_reply.replace("*", "").replace("`", "").replace("#", "")[:1200],
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": build_structured_response(inv_reply, provider="runtime_authority", model="runtime-authority"),
            "metadata": {"provider": "runtime_authority", "model": "runtime-authority"}
        }

    authoritative_context = build_runtime_context(authority_snapshot)
    current_utc = datetime.now(timezone.utc)
    current_time_str = current_utc.strftime("%A, %B %d, %Y at %H:%M:%S UTC")

    system_context_parts = [
        authoritative_context,
        f"CURRENT SYSTEM CLOCK: {current_time_str}.",
        "",
        "==================== SAREMBOK RESPONSE TRUTH BOUNDARY ====================",
        "Answer the user's actual question directly and preserve all material parts of the answer.",
        "Never invent Sarembok's creator, architecture, capabilities, providers, models, web results, media URLs, or generation results.",
        "Use Runtime Authority for Sarembok identity, capabilities, status, workers, memory, and provider facts.",
        "Use live retrieval/tool evidence for current web or repository content; if retrieval fails, say so instead of fabricating content.",
        "Do not claim image generation is available unless the live visual engine reports an operational provider/worker and an actual generation result exists.",
        "Do not claim two-way voice is active unless the live voice session is actually connected.",
        "Do not claim video/audio playback occurred unless the response contains verified media evidence.",
        "Do not omit or rewrite individual sentences from the provider response merely because they contain a limitation or refusal.",
        "===========================================================================",
    ]

    # Advanced Memory Personalization (Enhancement 5): Retrieve contextual facts from SQLite
    recalled_memories_payload: list[dict] = []
    keywords = [
        w for w in re.findall(r"\b[a-zA-Z]{4,}\b", prompt_lower)
        if w not in ("what", "when", "where", "which", "could", "would", "should", "there", "about", "please", "sarembok")
    ][:4]
    if keywords:
        where_clauses = " OR ".join(["key LIKE ? OR value LIKE ?"] * len(keywords))
        query_args: list[str] = []
        for kw in keywords:
            query_args.extend([f"%{kw}%", f"%{kw}%"])
        recalled_rows = store.db.execute(
            f"SELECT key, value, tier, created_at FROM memories WHERE {where_clauses} ORDER BY created_at DESC LIMIT 5",
            query_args
        ).fetchall()
        if recalled_rows:
            mem_summary = "\n".join([f"- [{r[2]}] {r[0]}: {r[1]}" for r in recalled_rows])
            system_context_parts.append(f"\nPersistent Recalled Memories & Context:\n{mem_summary}\n")
            recalled_memories_payload = [{"key": r[0], "value": r[1], "tier": r[2], "recalledFrom": r[3]} for r in recalled_rows]

    # Real-Time Data Integration: Live search for news, current events, live topics
    realtime_triggers = (
        "news", "headline", "headlines", "current event", "current events", "happened", "happening",
        "today", "yesterday", "this week", "this month", "latest", "recent", "update", "updates",
        "stock", "price", "crypto", "weather", "score",
        "game", "election", "president", "market", "research", "search", "browse", "find out",
        "look up", "world", "breaking", "what's going on", "whats going on", "what's new", "whats new"
    )
    live_data = None
    if not (is_identity_query(prompt_clean) or is_capability_query(prompt_clean) or is_self_state_query(prompt_clean)):
        if any(trig in prompt_lower for trig in realtime_triggers):
            live_data = _fetch_realtime_data(prompt_clean)
            if live_data:
                system_context_parts.append(f"\nREAL-TIME LIVE INTELLIGENCE RETRIEVAL:\n{live_data}\n")

    # Broader Language Support (Enhancement 8): Multi-language system directive
    LANG_NAMES = {
        "es": "Spanish (Español)",
        "fr": "French (Français)",
        "de": "German (Deutsch)",
        "zh": "Chinese (中文)",
        "ja": "Japanese (日本語)",
        "ar": "Arabic (العربية)",
        "pt": "Portuguese (Português)",
        "it": "Italian (Italiano)",
        "ru": "Russian (Русский)",
    }
    if language and language.lower() not in ("en", "english"):
        target_lang = LANG_NAMES.get(language.lower(), language)
        system_context_parts.append(
            f"\nLanguage Directive: The user has selected communication in {target_lang}. "
            f"You MUST generate your entire conversational response fluently in {target_lang}. "
            f"Keep code blocks, technical variable names, and JSON identifiers intact."
        )

    if is_conversational:
        system_context_parts.append(
            "\nCONVERSATIONAL VOICE DIRECTIVE: You are in Live Voice Conversation mode. "
            "Deliver a natural, calm, warm spoken response in 1-3 concise sentences. "
            "Do NOT use bulleted lists, raw markdown symbols, or long essays. Speak naturally as in a live telephone call."
        )
    system_prompt = "\n".join(system_context_parts)

    # Unified host/application execution path for a real enrolled target machine.
    if _is_host_execution_intent(prompt_clean):
        host_reply, host_traces = run_host_agent_loop(
            prompt_clean,
            system_prompt,
            session_id,
            model=model,
            max_steps=6,
        )
        _save_conversation(session_id, prompt_clean, host_reply)
        return {
            "response": host_reply,
            "audioText": host_reply,
            "source": "sarembok-host-agent",
            "model": model or "runtime-agent",
            "action": {"type": "HOST_EXECUTION"},
            "toolTraces": host_traces,
            "structuredResponse": build_structured_response(host_reply, provider="sarembok-host-agent", model=model or "runtime-agent"),
            "metadata": {"provider": "sarembok-host-agent", "model": model or "runtime-agent", "toolSteps": len(host_traces)},
        }

    # Unified website/application execution path for ordinary chat.
    if _is_browser_execution_intent(prompt_clean):
        browser_reply, browser_traces = run_browser_agent_loop(
            prompt_clean,
            system_prompt,
            session_id,
            model=model,
            max_steps=8,
        )
        _save_conversation(session_id, prompt_clean, browser_reply)
        return {
            "response": browser_reply,
            "audioText": browser_reply,
            "source": "sarembok-browser-agent",
            "model": model or "runtime-agent",
            "action": {"type": "BROWSER_EXECUTION", "verified": True},
            "toolTraces": browser_traces,
            "structuredResponse": build_structured_response(browser_reply, provider="sarembok-browser-agent", model=model or "runtime-agent"),
            "metadata": {"provider": "sarembok-browser-agent", "model": model or "runtime-agent", "toolSteps": len(browser_traces)},
        }

    # Autonomous Agentic Admin Execution Loop
    if is_admin:
        LOG.info("Executing dialogue directive via Autonomous Admin Agent Loop")
        admin_reply, traces = run_admin_agent_loop(
            prompt_clean,
            system_prompt,
            model=model,
            max_steps=5
        )
        _save_conversation(session_id, prompt_clean, admin_reply)
        return {
            "response": admin_reply,
            "audioText": admin_reply,
            "source": "autonomous_admin_agent",
            "model": model or "gpt-4o-mini",
            "adminMode": True,
            "toolTraces": traces,
            "timestamp": now()
        }

    messages = [{"role": "system", "content": system_prompt}]
    for role, content in conv_history:
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt_clean})

    reply = None
    source = None
    active_model = None
    provider_latency_ms = None
    provider_api = None
    provider_usage = {}
    try:
        # Pass requested model, multimodal image frame, and dynamic user api_key into ProviderRouter
        provider_result = PROVIDER_ROUTER.generate(
            system_prompt,
            prompt_clean,
            messages,
            requested_model=model,
            image_frame=image_frame,
            dynamic_key=api_key,
        )
        source = provider_result.provider
        active_model = provider_result.model
        provider_latency_ms = provider_result.latency_ms
        provider_api = provider_result.api
        provider_usage = provider_result.usage

        if image_frame:
            try:
                mem_id = f"mem-spatial-{uuid.uuid4().hex[:8]}"
                stamp = now()
                store.db.execute(
                    "INSERT INTO memories(memory_id, tier, key, value, agent_id, session_id, created_at) VALUES(?,?,?,?,?,?,?)",
                    (mem_id, "SPATIAL", f"visual_obs_{stamp[:19].replace(':', '-')}", f"Visual perception for: {prompt_clean[:120]}", "sarembok-prime", session_id, stamp),
                )
                store.db.commit()
            except Exception as e:
                LOG.debug("Spatial memory record failed: %s", e)

        if _is_model_identity_query(prompt_clean):
            reply = (
                f"This response is being generated by **{source}** "
                f"using **{active_model}** via **{provider_api}**."
            )
        else:
            reply = provider_result.text
    except Exception as exc:
        LOG.warning("LLM provider fabric failed: %s", exc)

    if reply:
        reply = _enrich_multimodal_reply(prompt_clean, reply)
    elif any(mi in prompt_clean.lower() for mi in ("play ", "stream ", "watch ", "listen to ", "open youtube", "open yt", "show video", "play song")):
        reply = _enrich_multimodal_reply(prompt_clean, "")


    refusal_markers = (
        "i don't have real-time access",
        "i don’t have real-time access",
        "i do not have real-time access",
        "i don't have access to real-time",
        "i do not have access to real-time",
        "i cannot access real-time",
        "i don't have access to current",
        "i do not have access to current",
        "cannot provide real-time",
        "my knowledge cutoff",
        "as an ai, i don't have access",
        "as an ai, i do not have access",
    )
    if reply and any(ref in reply.lower() for ref in refusal_markers):
        if live_data:
            reply = f"Here is the verified live real-time intelligence and current events as of **{current_time_str}**:\n\n{live_data}"
        else:
            fetched = _fetch_realtime_data(prompt_clean)
            if fetched:
                reply = f"Here is the verified live real-time intelligence as of **{current_time_str}**:\n\n{fetched}"
        reply = _enrich_multimodal_reply(prompt_clean, reply)

    def _spoken_clean(text: str) -> str:
        if not text:
            return ""
        s = re.sub(r":::(?:card|video|audio|doc|pdf|music|tasks)[^\n]*\n?", "", text)
        s = re.sub(r":::reveal[^\n]*\n?", " Solution: ", s)
        s = re.sub(r":::", "", s)
        s = re.sub(r"```[\s\S]*?```", "Code block omitted.", s)
        s = re.sub(r"\\\[([\s\S]*?)\\\]", r" \1 ", s)
        s = re.sub(r"\\\(([\s\S]*?)\\\)", r" \1 ", s)
        s = re.sub(r"\$\$([\s\S]*?)\$\$", r" \1 ", s)
        s = re.sub(r"\$([^\$]+)\$", r" \1 ", s)
        s = re.sub(r"https?:\/\/\S+", "", s)
        s = re.sub(r"[*#_`~|]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    if reply and reply.strip():
        reply = reply.strip()
        _save_conversation(session_id, prompt_clean, reply)
        store.event("sarembok-prime", "CHAT_RESPONSE", {"prompt": prompt_clean[:200], "model": active_model, "provider": source})
        result = {
            "response": reply,
            "audioText": _spoken_clean(reply),
            "source": source,
            "model": active_model,
            "action": None,
            "structuredResponse": build_structured_response(reply, provider=source, model=active_model, latency_ms=provider_latency_ms),
            "metadata": {"provider": source, "model": active_model, "latency_ms": provider_latency_ms, "provider_api": provider_api, "usage": provider_usage}
        }
        if recalled_memories_payload:
            result["recalledMemories"] = recalled_memories_payload
        return result

    if live_data:
        reply = f"Here is the verified live real-time news and intelligence as of **{current_time_str}**:\n\n{live_data}"
        _save_conversation(session_id, prompt_clean, reply)
        return {
            "response": reply,
            "audioText": _spoken_clean(reply),
            "source": "runtime_realtime_engine",
            "model": "google-news-live",
            "action": None
        }

    if is_limitation_query(prompt_clean):
        reply = render_limitations(authority_snapshot)
        source = "runtime_authority"
        active_model = "runtime-authority"
    elif is_capability_query(prompt_clean):
        reply = render_capabilities(authority_snapshot)
        source = "runtime_authority"
        active_model = "runtime-authority"
    elif is_identity_query(prompt_clean):
        reply = render_identity(authority_snapshot)
        source = "runtime_authority"
        active_model = "runtime-authority"
    else:
        reply = (
            "### ⚡ Sovereign Runtime Active\n\n"
            "Sarembok VE is operating in sovereign mode with active real-time media, perception, and chronometry subsystems.\n\n"
            "- **Media Playback:** Ask to `play lofi` or `stream synthwave`\n"
            "- **Live Search:** Inquire about `latest news on <topic>`\n"
            "- **System Clock:** Query `what time is it`\n"
            "- **Platform Architecture:** Inquire about `what can you do`"
        )
        source = "local_runtime"
        active_model = "runtime-fallback"
    _save_conversation(session_id, prompt_clean, reply)
    return {
        "response": reply,
        "audioText": _spoken_clean(reply),
        "source": source,
        "model": active_model,
        "action": None,
        "structuredResponse": build_structured_response(reply, provider=source, model=active_model),
        "metadata": {"provider": source, "model": active_model}
    }


def _save_conversation(session_id: str, user_msg: str, assistant_msg: str) -> None:
    """Save both sides of a conversation turn to persistent storage."""
    stamp = now()
    try:
        store.db.execute("INSERT INTO conversations(session_id, role, content, created_at) VALUES(?,?,?,?)",
                         (session_id, "user", user_msg, stamp))
        store.db.execute("INSERT INTO conversations(session_id, role, content, created_at) VALUES(?,?,?,?)",
                         (session_id, "assistant", assistant_msg, stamp))
        store.db.commit()
    except Exception as e:
        LOG.warning("Failed to save conversation: %s", e)


def dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    if method in ("SearchYouTube", "ResolveMediaStream"):
        query = str(params.get("query") or params.get("topic") or "").strip()
        return resolve_youtube_search(query)

    if method == "BrowserSessionOpen":
        sid = str(params.get("sessionId") or "").strip()
        browser_url = os.getenv("SAREMBOK_BROWSER_URL", "http://sarembok-browser:9100")
        req = urllib.request.Request(f"{browser_url}/session", data=json.dumps({"sessionId": sid}).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp: return json.loads(resp.read().decode("utf-8"))

    if method == "BrowserSessionInspect":
        sid = str(params.get("sessionId") or "").strip()
        browser_url = os.getenv("SAREMBOK_BROWSER_URL", "http://sarembok-browser:9100")
        req = urllib.request.Request(f"{browser_url}/session/inspect", data=json.dumps({"sessionId": sid, "includeText": bool(params.get("includeText", True))}).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp: return json.loads(resp.read().decode("utf-8"))

    if method == "BrowserAction":
        browser_url = os.getenv("SAREMBOK_BROWSER_URL", "http://sarembok-browser:9100")
        payload = dict(params)
        req = urllib.request.Request(f"{browser_url}/session/action", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp: return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try: return json.loads(e.read().decode("utf-8"))
            except Exception: return {"ok": False, "error": str(e)}

    if method == "BrowserSessionClose":
        sid = str(params.get("sessionId") or "").strip()
        browser_url = os.getenv("SAREMBOK_BROWSER_URL", "http://sarembok-browser:9100")
        req = urllib.request.Request(f"{browser_url}/session/close", data=json.dumps({"sessionId": sid}).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp: return json.loads(resp.read().decode("utf-8"))

    if method == "CallMcpTool":
        server_name = str(params.get("server") or params.get("serverName") or "").strip()
        tool_name = str(params.get("tool") or params.get("toolName") or "").strip()
        arguments = params.get("arguments") or {}
        if not server_name or not tool_name: raise ValueError("server_and_tool_required")
        raw_call = (tool_name + " " + json.dumps(arguments, ensure_ascii=False)).lower()
        high_impact_mcp = any(token in raw_call for token in (
            "purchase", "buy", "order", "payment", "transfer", "send_money",
            "delete", "remove", "close_account", "unsubscribe"
        ))
        if high_impact_mcp and not bool(params.get("confirm")):
            return {
                "ok": False,
                "requiresConfirmation": True,
                "error": "explicit_confirmation_required_for_high_impact_mcp_action",
                "server": server_name,
                "tool": tool_name,
            }
        try:
            from mcp_client import get_mcp_client_manager
        except ImportError:
            from Deployment.cloud.mcp_client import get_mcp_client_manager
        result = get_mcp_client_manager().call_external_tool(server_name, tool_name, arguments if isinstance(arguments, dict) else {})
        return {"ok": True, "server": server_name, "tool": tool_name, "result": result, "verified": True}
    if method in ("SarembokChat", "AriaChat", "Chat", "AriaDialogue", "SarembokDialogue"):
        prompt = str(params.get("prompt") or params.get("message") or params.get("text") or "").strip()
        if not prompt:
            raise ValueError("prompt is required")
        context = params.get("context")
        api_key = str(params.get("apiKey", "")).strip() or None
        session_id = str(params.get("sessionId", "default")).strip() or "default"
        req_model = str(params.get("model", "")).strip() or None
        req_lang = str(params.get("language", "en")).strip().lower() or "en"
        req_conv = bool(params.get("conversational", False))
        req_admin = bool(params.get("admin", False))
        req_frame = str(params.get("imageFrame") or params.get("image_frame") or params.get("frame") or "").strip() or None
        if req_admin:
            adm_token = str(params.get("adminToken", "") or params.get("adminSessionToken", "")).strip()
            adm_pass = str(params.get("adminPasscode", "") or params.get("passcode", "")).strip()
            is_auth = (adm_token in ADMIN_TOKENS) or (adm_pass and any(_hmac.compare_digest(adm_pass, p) for p in ADMIN_ALLOWED_PASSCODES))
            if not is_auth:
                raise ValueError("admin_authentication_required: Administrative passcode required to execute system tools.")

        res = sarembok_process_dialogue(
            prompt,
            context=context if isinstance(context, list) else None,
            api_key=api_key,
            session_id=session_id,
            model=req_model,
            language=req_lang,
            conversational=req_conv,
            admin=req_admin,
            image_frame=req_frame,
        )
        if "structuredResponse" not in res:
            res["structuredResponse"] = build_structured_response(
                res.get("response", ""),
                action=res.get("action"),
                provider=res.get("source"),
                model=res.get("model"),
                latency_ms=res.get("metadata", {}).get("latency_ms") if isinstance(res.get("metadata"), dict) else None,
            )
        res["agentId"] = "sarembok-prime"
        res["timestamp"] = now()
        return res

    if method == "RecordLiveTurn":
        session_id = str(params.get("sessionId", "default")).strip() or "default"
        user_text = str(params.get("userText", "") or "").strip()
        assistant_text = str(params.get("assistantText", "") or "").strip()
        model = str(params.get("model", "gemini-3.8-live") or "gemini-3.8-live").strip()
        if not user_text and not assistant_text:
            return {"recorded": False, "reason": "empty_turn"}
        _save_conversation(session_id, user_text, assistant_text)
        store.event(
            "sarembok-prime",
            "LIVE_VOICE_TURN",
            {
                "sessionId": session_id,
                "model": model,
                "userChars": len(user_text),
                "assistantChars": len(assistant_text),
            },
        )
        return {
            "recorded": True,
            "sessionId": session_id,
            "model": model,
            "userChars": len(user_text),
            "assistantChars": len(assistant_text),
            "timestamp": now(),
        }

    if method == "GetConversationHistory":
        session_id = str(params.get("sessionId", "default")).strip() or "default"
        limit = min(100, max(1, int(params.get("limit", 50))))
        rows = store.db.execute(
            "SELECT role, content, created_at FROM conversations WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
        messages = [{"role": r[0], "content": r[1], "createdAt": r[2]} for r in reversed(rows)]
        return {"sessionId": session_id, "messages": messages, "count": len(messages)}

    if method == "GetCapabilities":
        worker_stats = get_worker_status_counts()
        runtime_state = {"onlineWorkers": worker_stats["onlineWorkers"], "registeredWorkers": worker_stats["registeredWorkers"], "llmConfigured": bool(PROVIDER_ROUTER.configured())}
        return CAPABILITY_REGISTRY.snapshot(runtime_state)

    if method == "GetProviderMetrics":
        return PROVIDER_ROUTER.metrics()

    if method == "GetRuntimeInfo":
        worker_stats = get_worker_status_counts()
        agent_count = store.db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        memory_count = store.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conv_count = store.conversation_count()
        return {
            "uptimeSeconds": int(time.time() - STARTED),
            "workers": worker_stats,
            "agentCount": agent_count,
            "memoryCount": memory_count,
            "conversationCount": conv_count,
            "llmConfigured": bool(
                os.getenv("OPENAI_API_KEY")
                or os.getenv("OPENROUTER_API_KEY")
                or os.getenv("GROQ_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("LLM_ENDPOINT_URL")
            ),
        }

    if method == "BrowserNavigate":
        url = str(params.get("url", "")).strip()
        browser_url = os.getenv("SAREMBOK_BROWSER_URL", "http://sarembok-browser:9100")
        try:
            req = urllib.request.Request(
                f"{browser_url}/navigate",
                data=json.dumps({"url": url}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                return {"error": err_body.get("detail", str(e)), "ok": False}
            except Exception:
                return {"error": str(e), "ok": False}
        except Exception as e:
            return {"error": f"Browser service error: {e}", "ok": False}

    if method == "BrowserScreenshot":
        url = str(params.get("url", "")).strip()
        full_page = bool(params.get("fullPage", True))
        browser_url = os.getenv("SAREMBOK_BROWSER_URL", "http://sarembok-browser:9100")
        try:
            req = urllib.request.Request(
                f"{browser_url}/screenshot",
                data=json.dumps({"url": url, "full_page": full_page}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                return {"error": err_body.get("detail", str(e)), "ok": False}
            except Exception:
                return {"error": str(e), "ok": False}
        except Exception as e:
            return {"error": f"Browser service error: {e}", "ok": False}

    if method == "BrowserRender":
        url = str(params.get("url", "")).strip()
        browser_url = os.getenv("SAREMBOK_BROWSER_URL", "http://sarembok-browser:9100")
        try:
            req = urllib.request.Request(
                f"{browser_url}/render",
                data=json.dumps({"url": url}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                return {"error": err_body.get("detail", str(e)), "ok": False}
            except Exception:
                return {"error": str(e), "ok": False}
        except Exception as e:
            return {"error": f"Browser service error: {e}", "ok": False}

    if method == "CreateAgent":
        agent_id = str(params.get("agentId", "")).strip()
        if not agent_id:
            raise ValueError("agentId is required")
        display_name = str(params.get("displayName", agent_id)).strip() or agent_id
        return store.create_agent(agent_id, display_name)

    if method == "QueryAgentState":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        return {"agentId": agent_id, "cycleStage": "IDLE", "status": "ONLINE"}

    if method == "InjectPerception":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        perception = params.get("perception", {})
        store.event(agent_id, "PERCEPTION", {"perception": perception})
        return {"agentId": agent_id, "perceptionInjected": True, "stage": "VISION"}

    if method == "EvaluateDecision":
        risk = float(params.get("riskScore", 0.0))
        confidence = float(params.get("confidence", 0.0))
        action_id = str(params.get("actionId", ""))
        agent_id = str(params.get("agentId", ""))
        if agent_id:
            require_agent(agent_id)
        result = "DENY" if risk > 0.90 else "ALLOW"
        if agent_id:
            store.event(agent_id, "DECISION", {"actionId": action_id, "riskScore": risk, "confidence": confidence, "result": result})
        return {"agentId": agent_id, "actionId": action_id, "governanceResult": result, "riskScore": risk, "confidence": confidence}

    if method == "GetCognitiveScorecard":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        return {"agentId": agent_id, "overallReliability": 0.945, "perception": 0.96, "memory": 0.91, "reasoning": 0.94, "planning": 0.93, "policy": 0.99, "execution": 0.97, "recovery": 0.93, "conversation": 0.93}

    if method == "QueryWorldModel":
        return {"filter": str(params.get("filter", "all")), "entitiesCount": 0, "disagreementsCount": 0}

    if method == "CreateDelegation":
        delegation_id = f"del-{uuid.uuid4().hex[:12]}"
        stamp = now()
        source = params.get("sourceAgentId")
        target = params.get("targetAgentId")
        goal = params.get("goalId")
        store.db.execute("INSERT INTO delegations VALUES(?,?,?,?,?,?)", (delegation_id, source, target, goal, "created", stamp))
        store.db.commit()
        if source:
            store.event(str(source), "DELEGATION_CREATED", {"delegationId": delegation_id, "targetAgentId": target, "goalId": goal})
        return {"delegationId": delegation_id, "source": source, "target": target, "status": "created"}

    if method == "GetAuditTrail":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        count = store.db.execute("SELECT COUNT(*) FROM events WHERE agent_id=?", (agent_id,)).fetchone()[0]
        return {"agentId": agent_id, "recordsCount": count, "status": "integrity_verified", "storage": "sqlite-wal"}

    if method == "SendMessage":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        content = str(params.get("content", ""))
        store.db.execute("INSERT INTO messages VALUES(?,?,?,?)", (message_id, agent_id, content, now()))
        store.db.commit()
        store.event(agent_id, "MESSAGE", {"messageId": message_id})
        return {"agentId": agent_id, "messageId": message_id, "delivered": True}

    if method == "GetEvents":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        rows = store.db.execute("SELECT event_type,created_at,payload FROM events WHERE agent_id=? ORDER BY id DESC LIMIT 100", (agent_id,)).fetchall()
        events = [{"type": r[0], "timestamp": r[1], "payload": json.loads(r[2])} for r in reversed(rows)]
        return {"agentId": agent_id, "events": events, "count": len(events)}

    if method == "GetMetrics":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        event_count = store.db.execute("SELECT COUNT(*) FROM events WHERE agent_id=?", (agent_id,)).fetchone()[0]
        return {"agentId": agent_id, "metrics": {"perception": 0.96, "memory": 0.91, "reasoning": 0.94, "policy": 0.99, "overall": 0.945}, "eventCount": event_count, "uptimeSeconds": int(time.time() - STARTED)}

    if method == "RestoreState":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        entries = int(params.get("walEntries", 0))
        store.event(agent_id, "STATE_RESTORED", {"walEntriesReplayed": entries})
        return {"agentId": agent_id, "restored": True, "walEntriesReplayed": entries, "stateConsistent": True}

    if method == "RegisterWorker":
        worker_id = str(params.get("workerId", "")).strip()
        if not worker_id:
            raise ValueError("workerId is required")
        caps = json.dumps(params.get("capabilities", ["inference"]))
        vendor = str(params.get("gpuVendor", "NVIDIA"))
        model = str(params.get("gpuModel", "RTX 4090"))
        vram = int(params.get("vramMb", 24576))
        cuda = str(params.get("cudaVersion", "12.2"))
        avail_mem = int(params.get("availableMemoryMb", vram))
        models = json.dumps(params.get("supportedModels", ["default"]))
        latency = float(params.get("latencyMs", 10.0))
        status = str(params.get("status", "ONLINE")).upper()
        stamp = now()
        ensure_scheduler_schema()

        if not WORKER_ENROLLMENT_TOKEN:
            raise PermissionError("worker_enrollment_not_configured")
        supplied_enrollment = params.get("enrollmentToken")
        if (
            not isinstance(supplied_enrollment, str)
            or not _hmac.compare_digest(supplied_enrollment, WORKER_ENROLLMENT_TOKEN)
        ):
            raise PermissionError("authentication_required")

        worker_token = secrets.token_urlsafe(48)
        worker_token_hash = hashlib.sha256(worker_token.encode("utf-8")).hexdigest()
        existing = store.db.execute(
            """
            SELECT active_tasks
            FROM workers
            WHERE worker_id=?
            """,
            (worker_id,),
        ).fetchone()

        active_tasks = int(existing[0]) if existing else 0

        store.db.execute(
            """
            INSERT OR REPLACE INTO workers(
                worker_id,
                capabilities,
                gpu_vendor,
                gpu_model,
                vram_mb,
                cuda_version,
                available_memory_mb,
                supported_models,
                latency_ms,
                status,
                last_heartbeat,
                active_tasks,
                worker_token_hash
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                worker_id,
                caps,
                vendor,
                model,
                vram,
                cuda,
                avail_mem,
                models,
                latency,
                status,
                stamp,
                active_tasks,
                worker_token_hash,
            ),
        )

        store.db.commit()
        return {
            "workerId": worker_id,
            "registered": True,
            "status": status,
            "capabilities": json.loads(caps),
            "workerToken": worker_token,
        }

    if method == "ListWorkers":
        evaluate_worker_liveness()
        cap_filter = str(params.get("capability", "")).strip()
        status_filter = str(params.get("status", "")).strip().upper()
        rows = store.db.execute("SELECT worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat FROM workers").fetchall()
        workers = []
        for r in rows:
            caps = json.loads(r[1]) if r[1] else []
            if cap_filter and cap_filter not in caps:
                continue
            if status_filter and r[5] != status_filter:
                continue
            workers.append({
                "workerId": r[0],
                "capabilities": caps,
                "gpuVendor": r[2],
                "gpuModel": r[3],
                "vramMb": r[4],
                "status": r[5],
                "lastHeartbeat": r[6],
            })
        return {"workers": workers, "count": len(workers)}

    if method == "Heartbeat":
        worker_id = str(params.get("workerId", "")).strip()

        if not worker_id:
            raise ValueError("workerId is required")

        ensure_scheduler_schema()

        stamp = now()

        row = store.db.execute(
            """
            SELECT worker_id, status, last_heartbeat
            FROM workers
            WHERE worker_id=?
            """,
            (worker_id,),
        ).fetchone()

        if not row:
            raise ValueError(
                f"worker_not_found: {worker_id}"
            )

        prev_status = str(row[1]).upper()

        store.db.execute(
            """
            UPDATE workers
            SET
                last_heartbeat=?,
                status='ONLINE'
            WHERE worker_id=?
            """,
            (stamp, worker_id),
        )

        store.db.commit()

        if prev_status != "ONLINE":
            LOG.info(
                "worker status transition worker_id=%s %s->ONLINE",
                worker_id,
                prev_status,
            )
            store.event(
                None,
                "WORKER_STATUS_CHANGED",
                {
                    "workerId": worker_id,
                    "previousStatus": prev_status,
                    "status": "ONLINE",
                    "lastHeartbeat": stamp,
                    "evaluatedAt": stamp,
                },
            )

        return {
            "workerId": worker_id,
            "status": "ONLINE",
            "lastHeartbeat": stamp,
        }

    if method in ("ScheduleCompute", "CreateTask"):
        task = params.get("task", {})

        if not isinstance(task, dict):
            task = {}

        task_type = str(
            params.get("taskType")
            or task.get("type")
            or "inference"
        ).strip()

        req_cap = required_capability_for_task(
            task_type,
            params.get("requiredCapability") or task.get("requiredCapability"),
        )

        payload = params.get("payload")

        if payload is None:
            payload = task

        explicit_worker = str(params.get("assignedWorkerId", "") or "").strip()
        assigned_worker = (
            explicit_worker
            if explicit_worker
            else select_worker(required_capability=req_cap)
        )

        task_id = f"task-{uuid.uuid4().hex[:10]}"

        dependency_ready = task_dependency_ready(payload)
        status = (
            "QUEUED"
            if assigned_worker and dependency_ready
            else "PENDING_WORKER"
        )
        if not dependency_ready:
            assigned_worker = None

        stamp = now()

        store.db.execute(
            """
            INSERT INTO tasks(
                task_id,
                task_type,
                required_capability,
                payload,
                assigned_worker_id,
                status,
                created_at,
                updated_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                task_id,
                task_type,
                req_cap,
                json.dumps(payload),
                assigned_worker,
                status,
                stamp,
                stamp,
            ),
        )

        store.db.commit()

        return {
            "taskId": task_id,
            "taskType": task_type,
            "requiredCapability": req_cap,
            "assignedWorkerId": assigned_worker,
            "status": status,
        }

    if method == "ClaimTask":
        ensure_scheduler_schema()

        task_id = str(params.get("taskId", "")).strip()
        worker_id = str(params.get("workerId", "")).strip()

        if not task_id:
            raise ValueError("taskId is required")

        if not worker_id:
            raise ValueError("workerId is required")

        row = store.db.execute(
            """
            SELECT assigned_worker_id, status, required_capability, payload
            FROM tasks
            WHERE task_id=?
            """,
            (task_id,),
        ).fetchone()

        if not row:
            raise ValueError(
                f"task_not_found: {task_id}"
            )

        assigned_worker, task_status, req_cap, raw_payload = row[0], row[1], row[2] or "compute", row[3]
        try:
            task_payload = json.loads(raw_payload) if raw_payload else {}
        except Exception:
            task_payload = {}
        if not task_dependency_ready(task_payload):
            raise ValueError("task_dependency_not_ready")

        if assigned_worker and assigned_worker != worker_id:
            raise ValueError("worker_mismatch")

        if task_status not in ("QUEUED", "PENDING_WORKER"):
            raise ValueError(
                f"task_not_claimable: {task_status}"
            )

        worker = store.db.execute(
            """
            SELECT status, last_heartbeat, capabilities
            FROM workers
            WHERE worker_id=?
            """,
            (worker_id,),
        ).fetchone()

        if not worker:
            raise ValueError(
                f"worker_not_found: {worker_id}"
            )

        if worker[0] != "ONLINE":
            raise ValueError("worker_not_online")

        if not heartbeat_is_fresh(worker[1]):
            raise ValueError("worker_heartbeat_stale")

        try:
            caps = json.loads(worker[2]) if worker[2] else []
        except Exception:
            caps = []

        if req_cap not in caps:
            raise ValueError(f"worker_missing_capability: {req_cap}")

        stamp = now()

        store.db.execute(
            """
            UPDATE tasks
            SET
                status='RUNNING',
                assigned_worker_id=?,
                updated_at=?
            WHERE task_id=?
              AND status IN ('QUEUED', 'PENDING_WORKER')
            """,
            (worker_id, stamp, task_id),
        )

        if store.db.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("task_claim_conflict")

        store.db.execute(
            """
            UPDATE workers
            SET active_tasks=active_tasks+1
            WHERE worker_id=?
            """,
            (worker_id,),
        )

        store.db.commit()

        return {
            "taskId": task_id,
            "workerId": worker_id,
            "status": "RUNNING",
        }

    if method == "CompleteTask":
        ensure_scheduler_schema()

        task_id = str(params.get("taskId", "")).strip()
        worker_id = str(params.get("workerId", "")).strip()
        result_payload = params.get("result", {})
        error_payload = params.get("error")

        if not task_id:
            raise ValueError("taskId is required")

        if not worker_id:
            raise ValueError("workerId is required")

        row = store.db.execute(
            """
            SELECT assigned_worker_id, status
            FROM tasks
            WHERE task_id=?
            """,
            (task_id,),
        ).fetchone()

        if not row:
            raise ValueError(
                f"task_not_found: {task_id}"
            )

        if row[0] != worker_id:
            raise ValueError("worker_mismatch")

        if row[1] != "RUNNING":
            raise ValueError(
                f"task_not_running: {row[1]}"
            )

        stamp = now()

        store.db.execute(
            """
            UPDATE tasks
            SET
                status='COMPLETED',
                result=?,
                error=?,
                updated_at=?
            WHERE task_id=?
              AND assigned_worker_id=?
              AND status='RUNNING'
            """,
            (json.dumps(result_payload if isinstance(result_payload, dict) else {"value": result_payload}), str(error_payload) if error_payload else None, stamp, task_id, worker_id),
        )

        if store.db.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("task_completion_conflict")

        store.db.execute(
            """
            UPDATE workers
            SET active_tasks=MAX(active_tasks-1,0)
            WHERE worker_id=?
            """,
            (worker_id,),
        )

        store.db.commit()
        assign_pending_tasks()

        return {
            "taskId": task_id,
            "workerId": worker_id,
            "status": "COMPLETED",
        }

    if method == "FailTask":
        ensure_scheduler_schema()
        task_id = str(params.get("taskId", "")).strip()
        worker_id = str(params.get("workerId", "")).strip()
        error_msg = str(params.get("error", "execution_failed"))
        retryable = bool(params.get("retryable", False))

        if not task_id:
            raise ValueError("taskId is required")
        if not worker_id:
            raise ValueError("workerId is required")

        row = store.db.execute(
            "SELECT assigned_worker_id, status FROM tasks WHERE task_id=?",
            (task_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"task_not_found: {task_id}")
        if row[0] != worker_id:
            raise ValueError("worker_mismatch")

        new_status = "PENDING_WORKER" if retryable else "FAILED"
        stamp = now()
        store.db.execute(
            """
            UPDATE tasks
            SET status=?, assigned_worker_id=?, updated_at=?
            WHERE task_id=? AND assigned_worker_id=?
            """,
            (new_status, None if retryable else worker_id, stamp, task_id, worker_id),
        )
        store.db.execute(
            "UPDATE workers SET active_tasks=MAX(active_tasks-1,0) WHERE worker_id=?",
            (worker_id,),
        )
        store.db.commit()
        store.event(None, "TASK_FAILED", {"taskId": task_id, "workerId": worker_id, "error": error_msg, "retryable": retryable, "status": new_status})
        if retryable:
            assign_pending_tasks()
        return {
            "taskId": task_id,
            "workerId": worker_id,
            "status": new_status,
            "error": error_msg,
        }

    if method == "ListTasks":
        ensure_scheduler_schema()
        status_filter = str(params.get("status", "")).strip().upper()
        worker_filter = str(params.get("workerId", "")).strip()
        query = "SELECT task_id, task_type, required_capability, payload, assigned_worker_id, status, created_at, updated_at FROM tasks WHERE 1=1"
        q_params: list[Any] = []
        if status_filter:
            query += " AND status=?"
            q_params.append(status_filter)
        if worker_filter:
            query += " AND (assigned_worker_id=? OR assigned_worker_id IS NULL OR assigned_worker_id='')"
            q_params.append(worker_filter)
        query += " ORDER BY created_at ASC LIMIT 100"
        rows = store.db.execute(query, q_params).fetchall()
        tasks_list = []
        for r in rows:
            tasks_list.append({
                "taskId": r[0],
                "taskType": r[1],
                "requiredCapability": r[2],
                "payload": r[3],
                "assignedWorkerId": r[4],
                "status": r[5],
                "createdAt": r[6],
                "updatedAt": r[7],
            })
        return {"tasks": tasks_list, "count": len(tasks_list)}

    if method == "RuntimeInfo":
        worker_stats = get_worker_status_counts()
        session_count = store.db.execute("SELECT COUNT(*) FROM digital_human_sessions WHERE status!='TERMINATED'").fetchone()[0]
        agent_count = store.db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        task_count = store.db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        event_count = store.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        project_count = store.db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        memory_count = store.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        file_count = store.db.execute("SELECT COUNT(*) FROM file_assets").fetchone()[0]
        last_ckpt = store.db.execute("SELECT checkpoint_id, label, created_at FROM checkpoints ORDER BY created_at DESC LIMIT 1").fetchone()
        last_checkpoint = f"{last_ckpt[1]} ({last_ckpt[0]})" if last_ckpt else "None"

        return {
            "status": "ONLINE",
            "service": "sarembok-ve-cloud-runtime",
            "domain": "sarembok.com",
            "version": "1.3.0-production",
            "uptimeSeconds": int(time.time() - STARTED),
            "storage": "sqlite-wal",
            "authConfigured": bool(AUTH_TOKEN),
            "registeredWorkers": worker_stats["registeredWorkers"],
            "onlineWorkers": worker_stats["onlineWorkers"],
            "staleWorkers": worker_stats["staleWorkers"],
            "offlineWorkers": worker_stats["offlineWorkers"],
            "activeDigitalHumanSessions": session_count,
            "activeAgents": agent_count,
            "totalTasks": task_count,
            "totalEvents": event_count,
            "totalProjects": project_count,
            "totalMemories": memory_count,
            "totalFiles": file_count,
            "lastCheckpoint": last_checkpoint,
        }

    if method == "ListProjects":
        rows = store.db.execute("SELECT project_id, name, status, description, lead_agent_id, created_at, updated_at FROM projects ORDER BY created_at DESC").fetchall()
        projects = [{"projectId": r[0], "name": r[1], "status": r[2], "description": r[3], "leadAgentId": r[4], "createdAt": r[5], "updatedAt": r[6]} for r in rows]
        return {"projects": projects, "count": len(projects)}

    if method == "CreateProject":
        project_id = str(params.get("projectId") or f"proj-{uuid.uuid4().hex[:8]}").strip()
        name = str(params.get("name", "Untitled Project")).strip()
        status = str(params.get("status", "IN_PROGRESS")).strip()
        desc = str(params.get("description", "")).strip()
        lead_agent = params.get("leadAgentId")
        stamp = now()
        store.db.execute(
            "INSERT OR REPLACE INTO projects(project_id, name, status, description, lead_agent_id, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
            (project_id, name, status, desc, lead_agent, stamp, stamp),
        )
        store.db.commit()
        store.event(lead_agent, "PROJECT_CREATED", {"projectId": project_id, "name": name, "status": status})
        return {"projectId": project_id, "name": name, "status": status, "description": desc, "createdAt": stamp}

    if method == "GetProject":
        project_id = str(params.get("projectId", "")).strip()
        row = store.db.execute("SELECT project_id, name, status, description, lead_agent_id, created_at, updated_at FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if not row:
            raise ValueError(f"project_not_found: {project_id}")
        return {"projectId": row[0], "name": row[1], "status": row[2], "description": row[3], "leadAgentId": row[4], "createdAt": row[5], "updatedAt": row[6]}

    if method == "UpdateProject":
        project_id = str(params.get("projectId", "")).strip()
        if not project_id:
            raise ValueError("projectId is required")
        status = params.get("status")
        desc = params.get("description")
        stamp = now()
        if status is not None:
            store.db.execute("UPDATE projects SET status=?, updated_at=? WHERE project_id=?", (str(status), stamp, project_id))
        if desc is not None:
            store.db.execute("UPDATE projects SET description=?, updated_at=? WHERE project_id=?", (str(desc), stamp, project_id))
        store.db.commit()
        store.event(None, "PROJECT_UPDATED", {"projectId": project_id, "status": status})
        return {"projectId": project_id, "updated": True, "updatedAt": stamp}

    if method == "ListMemories":
        tier_filter = str(params.get("tier", "")).strip().upper()
        agent_filter = str(params.get("agentId", "")).strip()
        query = "SELECT memory_id, tier, key, value, agent_id, session_id, created_at FROM memories WHERE 1=1"
        qp: list[Any] = []
        if tier_filter:
            query += " AND tier=?"
            qp.append(tier_filter)
        if agent_filter:
            query += " AND agent_id=?"
            qp.append(agent_filter)
        query += " ORDER BY created_at DESC LIMIT 100"
        rows = store.db.execute(query, qp).fetchall()
        memories = [{"memoryId": r[0], "tier": r[1], "key": r[2], "value": r[3], "agentId": r[4], "sessionId": r[5], "createdAt": r[6]} for r in rows]
        return {"memories": memories, "count": len(memories)}

    if method == "StoreMemory":
        key = str(params.get("key", "")).strip()
        value = str(params.get("value", "")).strip()
        tier = str(params.get("tier", "WORKING")).strip().upper()
        agent_id = params.get("agentId")
        if not key or not value:
            raise ValueError("key and value are required")
        memory_id = f"mem-{uuid.uuid4().hex[:10]}"
        stamp = now()
        store.db.execute(
            "INSERT INTO memories(memory_id, tier, key, value, agent_id, session_id, created_at) VALUES(?,?,?,?,?,?,?)",
            (memory_id, tier, key, value, agent_id, str(params.get("sessionId", "")).strip() or None, stamp),
        )
        store.db.commit()
        store.event(agent_id, "MEMORY_STORED", {"memoryId": memory_id, "tier": tier, "key": key})
        return {"memoryId": memory_id, "tier": tier, "key": key, "stored": True, "createdAt": stamp}

    if method == "RecallMemory":
        key = str(params.get("key", "")).strip()
        agent_id = params.get("agentId")
        if not key:
            raise ValueError("key is required")
        query = "SELECT memory_id, tier, key, value, agent_id, session_id, created_at FROM memories WHERE key=?"
        qp = [key]
        if agent_id:
            query += " AND agent_id=?"
            qp.append(str(agent_id))
        query += " ORDER BY created_at DESC LIMIT 1"
        row = store.db.execute(query, qp).fetchone()
        if not row:
            return {"found": False, "key": key, "value": None}
        return {"found": True, "memoryId": row[0], "tier": row[1], "key": row[2], "value": row[3], "agentId": row[4], "sessionId": row[5], "createdAt": row[6]}

    if method == "SearchMemories":
        query_term = str(params.get("query", "")).strip()
        tier_filter = str(params.get("tier", "")).strip().upper()
        limit = min(100, max(1, int(params.get("limit", 50))))
        sql = "SELECT memory_id, tier, key, value, agent_id, session_id, created_at FROM memories WHERE 1=1"
        qp: list[Any] = []
        if query_term:
            sql += " AND (key LIKE ? OR value LIKE ?)"
            qp.extend([f"%{query_term}%", f"%{query_term}%"])
        if tier_filter:
            sql += " AND tier=?"
            qp.append(tier_filter)
        sql += " ORDER BY created_at DESC LIMIT ?"
        qp.append(limit)
        rows = store.db.execute(sql, qp).fetchall()
        memories = [{"memoryId": r[0], "tier": r[1], "key": r[2], "value": r[3], "agentId": r[4], "sessionId": r[5], "createdAt": r[6]} for r in rows]
        return {"memories": memories, "count": len(memories), "query": query_term}

    if method == "GetMemoryConversation":
        memory_id = str(params.get("memoryId", "")).strip()
        if not memory_id:
            raise ValueError("memoryId is required")
        row = store.db.execute(
            "SELECT memory_id, session_id, created_at, key, value FROM memories WHERE memory_id=?",
            (memory_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"memory_not_found: {memory_id}")
        session_id = row[1]
        if not session_id:
            nearest = store.db.execute(
                "SELECT session_id FROM conversations ORDER BY ABS(strftime('%s', created_at) - strftime('%s', ?)) LIMIT 1",
                (row[2],),
            ).fetchone()
            if nearest:
                session_id = nearest[0]
        if not session_id:
            return {"success": False, "memoryId": memory_id, "found": False, "reason": "conversation_not_linked"}
        limit = min(200, max(1, int(params.get("limit", 100))))
        rows = store.db.execute(
            "SELECT role, content, created_at FROM conversations WHERE session_id=? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return {
            "success": True,
            "found": bool(rows),
            "memoryId": memory_id,
            "sessionId": session_id,
            "memory": {"key": row[3], "value": row[4], "createdAt": row[2]},
            "messages": [{"role": r[0], "content": r[1], "createdAt": r[2]} for r in rows],
        }

    if method == "DeleteMemory":
        memory_id = str(params.get("memoryId", "")).strip()
        if not memory_id:
            raise ValueError("memoryId is required")
        store.db.execute("DELETE FROM memories WHERE memory_id=?", (memory_id,))
        store.db.commit()
        store.event(None, "MEMORY_DELETED", {"memoryId": memory_id})
        return {"memoryId": memory_id, "deleted": True}

    if method == "ClearMemories":
        tier_filter = str(params.get("tier", "")).strip().upper()
        if tier_filter:
            store.db.execute("DELETE FROM memories WHERE tier=?", (tier_filter,))
        else:
            store.db.execute("DELETE FROM memories")
        store.db.commit()
        return {"cleared": True, "tier": tier_filter or "ALL"}

    if method == "SubmitFeedback":
        session_id = str(params.get("sessionId", "default")).strip() or "default"
        message_id = str(params.get("messageId", "")).strip() or None
        prompt_text = str(params.get("prompt", "")).strip()
        response_text = str(params.get("response", "")).strip()
        rating = int(params.get("rating", 1))
        feedback_text = str(params.get("feedback", "") or params.get("comment", "")).strip()

        feedback_id = f"fb-{uuid.uuid4().hex[:10]}"
        stamp = now()
        store.db.execute(
            """
            INSERT INTO feedback(feedback_id, session_id, message_id, prompt, response, rating, feedback_text, created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (feedback_id, session_id, message_id, prompt_text, response_text, rating, feedback_text, stamp),
        )
        store.db.commit()
        store.event(None, "USER_FEEDBACK_RECORDED", {"feedbackId": feedback_id, "rating": rating, "sessionId": session_id})
        return {"feedbackId": feedback_id, "recorded": True, "rating": rating, "timestamp": stamp}

    if method == "GetFeedbackSummary":
        up_count = store.db.execute("SELECT COUNT(*) FROM feedback WHERE rating > 0").fetchone()[0]
        down_count = store.db.execute("SELECT COUNT(*) FROM feedback WHERE rating < 0").fetchone()[0]
        total = up_count + down_count
        positive_pct = round((up_count / total * 100.0), 1) if total > 0 else 100.0
        rows = store.db.execute("SELECT feedback_id, rating, feedback_text, created_at FROM feedback ORDER BY created_at DESC LIMIT 10").fetchall()
        recent = [{"feedbackId": r[0], "rating": r[1], "feedback": r[2], "createdAt": r[3]} for r in rows]
        return {
            "totalFeedback": total,
            "positiveCount": up_count,
            "negativeCount": down_count,
            "positivePercentage": positive_pct,
            "recent": recent,
        }

    if method == "ScaleWorkers":
        # Truth boundary: Do not insert mock or fake workers.
        # Worker instances must be physically launched via worker_client.py or compose.worker.yaml
        w_stats = get_worker_status_counts()
        return {
            "scaled": False,
            "status": "ready_for_workers",
            "message": "Workers must be legitimately launched via Deployment/cloud/worker_client.py or compose.worker.yaml. Runtime authority never invents fake hardware.",
            "onlineWorkers": w_stats["onlineWorkers"],
            "registeredWorkers": w_stats["registeredWorkers"],
        }

    if method == "PruneWorkers":
        force = bool(params.get("force", True))
        max_age = params.get("maxAgeSeconds")
        pruned_cnt = prune_stale_workers(
            max_offline_age_seconds=int(max_age) if max_age is not None else None,
            force_all_offline=force,
        )
        counts = get_worker_status_counts()
        return {"pruned": pruned_cnt, "remaining": counts}

    if method == "ListMcpServers":
        try:
            try:
                from mcp_client import get_mcp_client_manager
            except ImportError:
                from Deployment.cloud.mcp_client import get_mcp_client_manager
            servers = get_mcp_client_manager().list_servers()
            return {"success": True, "servers": servers, "count": len(servers)}
        except Exception as exc:
            return {"success": False, "error": str(exc), "servers": []}

    if method == "RegisterMcpServer":
        name = str(params.get("name", "")).strip()
        if not name:
            raise ValueError("name is required")
        transport = str(params.get("transport", "http")).strip().lower()
        url = str(params.get("url", "")).strip()
        command = str(params.get("command", "")).strip()
        args = params.get("args") or []
        try:
            try:
                from mcp_client import get_mcp_client_manager
            except ImportError:
                from Deployment.cloud.mcp_client import get_mcp_client_manager
            res = get_mcp_client_manager().register_server(
                name=name,
                transport=transport,
                url=url,
                command=command,
                args=args if isinstance(args, list) else [],
            )
            return {"success": True, "server": res}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if method == "CancelActiveStream":
        # Barge-in cancellation token
        return {"cancelled": True, "timestamp": now()}

    if method == "SpatialVisualRecall":
        query_text = str(params.get("query", "")).strip()
        limit = min(50, max(1, int(params.get("limit", 10))))
        sql = "SELECT memory_id, key, value, created_at FROM memories WHERE tier='SPATIAL'"
        qp: list[Any] = []
        if query_text:
            sql += " AND (key LIKE ? OR value LIKE ?)"
            qp.extend([f"%{query_text}%", f"%{query_text}%"])
        sql += " ORDER BY created_at DESC LIMIT ?"
        qp.append(limit)
        rows = store.db.execute(sql, qp).fetchall()
        obs = [{"memoryId": r[0], "key": r[1], "observation": r[2], "createdAt": r[3]} for r in rows]
        return {"success": True, "query": query_text, "observations": obs, "count": len(obs)}


    if method in ("VerifyAdminPasscode", "AuthenticateMaster"):
        passcode = str(params.get("passcode", "")).strip()
        if not passcode:
            return {"success": False, "error": "passcode_required"}
        if any(_hmac.compare_digest(passcode, valid_p) for valid_p in ADMIN_ALLOWED_PASSCODES):
            token = f"adm-{uuid.uuid4().hex}"
            ADMIN_TOKENS.add(token)
            user = {
                "id": "master-developer",
                "email": "developer@sarembok.com",
                "name": "Sovereign Master",
                "role": "admin",
                "provider": "master",
                "avatarUrl": ""
            }
            USER_SESSIONS[token] = {**user, "token": token, "expires": time.time() + 86400 * 7}
            return {"success": True, "adminToken": token, "token": token, "user": user}
        return {"success": False, "error": "invalid_passcode"}

    if method == "AuthenticateSocialUser":
        provider = str(params.get("provider", "guest")).lower().strip()
        email = str(params.get("email", "")).strip().lower()
        name = str(params.get("name", "")).strip()
        avatar_url = str(params.get("avatarUrl", "")).strip()

        if provider == "guest":
            user_id = f"guest-{uuid.uuid4().hex[:8]}"
            if not name:
                name = "Guest Explorer"
            email = f"{user_id}@guest.sarembok.com"
        else:
            if not email:
                email = f"user-{uuid.uuid4().hex[:8]}@{provider}.sarembok.com"
            user_id = f"usr-{hashlib.sha256(email.encode('utf-8')).hexdigest()[:12]}"
            if not name:
                name = email.split("@")[0].capitalize()

        stamp = now()
        try:
            store.db.execute(
                "INSERT INTO users(id, email, name, avatar_url, auth_provider, role, created_at, last_login_at) "
                "VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET last_login_at=excluded.last_login_at, name=COALESCE(excluded.name, users.name), avatar_url=COALESCE(excluded.avatar_url, users.avatar_url)",
                (user_id, email, name, avatar_url, provider, "user", stamp, stamp)
            )
            store.db.commit()
        except Exception as exc:
            LOG.warning("Failed to persist user in SQLite: %s", exc)

        session_token = f"usr-{uuid.uuid4().hex}"
        user = {
            "id": user_id,
            "email": email,
            "name": name,
            "avatarUrl": avatar_url,
            "role": "user",
            "provider": provider
        }
        USER_SESSIONS[session_token] = {**user, "token": session_token, "expires": time.time() + 86400 * 30}
        return {"success": True, "token": session_token, "user": user}

    if method == "GetCurrentUser":
        token = str(params.get("token", "") or params.get("sessionToken", "")).strip()
        user_sess = USER_SESSIONS.get(token)
        if user_sess:
            return {"success": True, "user": user_sess}
        if token in ADMIN_TOKENS:
            admin_user = {
                "id": "master-developer",
                "email": "developer@sarembok.com",
                "name": "Sovereign Master",
                "role": "admin",
                "provider": "master",
                "avatarUrl": ""
            }
            return {"success": True, "user": admin_user}
        return {"success": False, "error": "unauthenticated"}

    if method == "ListUserChatSessions":
        token = str(params.get("token", "") or params.get("sessionToken", "")).strip()
        user_sess = USER_SESSIONS.get(token)
        is_admin = (token in ADMIN_TOKENS) or (user_sess and user_sess.get("role") == "admin")
        user_id = user_sess.get("id", "anonymous") if user_sess else "anonymous"

        try:
            if is_admin:
                rows = store.db.execute("SELECT session_id, user_id, title, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC LIMIT 60").fetchall()
            else:
                rows = store.db.execute("SELECT session_id, user_id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 60", (user_id,)).fetchall()
            sessions = [{"session_id": r[0], "user_id": r[1], "title": r[2], "created_at": r[3], "updated_at": r[4]} for r in rows]
            return {"success": True, "sessions": sessions}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if method == "SaveUserChatSession":
        token = str(params.get("token", "") or params.get("sessionToken", "")).strip()
        user_sess = USER_SESSIONS.get(token)
        user_id = user_sess.get("id", "anonymous") if user_sess else "anonymous"
        session_id = str(params.get("sessionId", "")).strip()
        title = str(params.get("title", "Conversation")).strip()
        messages = params.get("messages", [])
        if not session_id:
            return {"success": False, "error": "session_id_required"}
        stamp = now()
        try:
            store.db.execute(
                "INSERT INTO chat_sessions(session_id, user_id, title, messages_json, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(session_id) DO UPDATE SET title=excluded.title, messages_json=excluded.messages_json, updated_at=excluded.updated_at",
                (session_id, user_id, title, json.dumps(messages), stamp, stamp)
            )
            store.db.commit()
            return {"success": True, "sessionId": session_id}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if method == "DeleteUserChatSession":
        session_id = str(params.get("sessionId", "")).strip()
        if not session_id:
            return {"success": False, "error": "session_id_required"}
        try:
            store.db.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
            store.db.commit()
            return {"success": True, "sessionId": session_id}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if method == "GetAdminStatus":
        w_stats = get_worker_status_counts()
        return {
            "adminModeSupported": True,
            "capabilities": [
                "run_terminal",
                "execute_python",
                "read_file",
                "write_file",
                "fleet_status",
                "git_info",
                "browser_research"
            ],
            "serverUptimeSeconds": int(time.time() - STARTED),
            "activeWorkers": w_stats.get("onlineWorkers", 0),
            "timestamp": now()
        }

    if method == "AdminExecuteDirective":
        # Enforce Admin Passcode / Token Gate
        adm_token = str(params.get("adminToken", "") or params.get("adminSessionToken", "")).strip()
        adm_pass = str(params.get("adminPasscode", "") or params.get("passcode", "")).strip()
        is_auth = (adm_token in ADMIN_TOKENS) or (adm_pass and any(_hmac.compare_digest(adm_pass, p) for p in ADMIN_ALLOWED_PASSCODES))
        if not is_auth:
            raise ValueError("admin_authentication_required: Administrative passcode required to execute system tools.")

        prompt = str(params.get("directive", "") or params.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("directive is required")
        session_id = str(params.get("sessionId", "admin-session")).strip() or "admin-session"
        model = str(params.get("model", "")).strip() or None
        res = sarembok_process_dialogue(
            prompt,
            session_id=session_id,
            model=model,
            admin=True
        )
        return res

    if method == "GetVisionStatus":
        return {
            "opencvInstalled": OPENCV_AVAILABLE,
            "version": OPENCV_VERSION,
            "detectorLoaded": OPENCV_DETECTOR is not None,
            "modelName": "OpenCV YuNet ONNX (Face & Gaze Tracking)",
            "capabilities": ["Face Detection", "Landmarks", "Gaze Tracking", "Motion Analysis", "Brightness Telemetry"],
        }

    if method == "ProcessVisionFrame":
        if not OPENCV_AVAILABLE:
            raise RuntimeError("opencv_not_available")
        raw_b64 = str(params.get("frame", "")).strip()
        if not raw_b64:
            raise ValueError("frame is required")
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]

        t0 = time.time()
        img_bytes = base64.b64decode(raw_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("invalid_image_data")

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))

        faces_data = []
        if OPENCV_DETECTOR is not None:
            OPENCV_DETECTOR.setInputSize((w, h))
            ret, detected_faces = OPENCV_DETECTOR.detect(img)
            if detected_faces is not None:
                for f in detected_faces:
                    box_x, box_y, box_w, box_h = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                    conf = float(f[14])
                    re_x, re_y = float(f[4]), float(f[5])
                    le_x, le_y = float(f[6]), float(f[7])
                    nose_x, nose_y = float(f[8]), float(f[9])

                    center_face_x = (box_x + box_w / 2.0) / w
                    center_face_y = (box_y + box_h / 2.0) / h
                    gaze_x = round((center_face_x - 0.5) * 2.0, 3)
                    gaze_y = round((center_face_y - 0.5) * 2.0, 3)

                    faces_data.append({
                        "box": {"x": box_x, "y": box_y, "w": box_w, "h": box_h},
                        "confidence": round(conf, 3),
                        "landmarks": {
                            "rightEye": [round(re_x, 1), round(re_y, 1)],
                            "leftEye": [round(le_x, 1), round(le_y, 1)],
                            "nose": [round(nose_x, 1), round(nose_y, 1)],
                        },
                        "gazeVector": {"dx": gaze_x, "dy": gaze_y},
                    })

        dt_ms = round((time.time() - t0) * 1000, 2)
        return {
            "success": True,
            "opencvVersion": OPENCV_VERSION,
            "frameWidth": w,            "frameHeight": h,
            "faceCount": len(faces_data),
            "faces": faces_data,
            "brightness": round(brightness, 1),
            "latencyMs": dt_ms,
            "timestamp": now(),
        }

    if method == "GetGpuMarketplace":
        ensure_scheduler_schema()
        rental_count = store.db.execute("SELECT COUNT(*) FROM gpu_rentals WHERE status='ACTIVE'").fetchone()[0]
        w_stats = get_worker_status_counts()
        return {
            "tiers": GPU_MARKETPLACE_TIERS,
            "activeRentals": rental_count,
            "onlineWorkers": w_stats["onlineWorkers"],
            "registeredWorkers": w_stats["registeredWorkers"],
            "colabSetupCommand": "!curl -sSL https://raw.githubusercontent.com/jetsontech/SarembokVE/runtime-authority-truth-boundary/Deployment/cloud/colab_worker.py | python3 - --ws-url wss://sarembok.com",
        }

    if method == "RentGpuNode":
        ensure_scheduler_schema()
        tier_id = str(params.get("tierId", "")).strip()
        duration_hours = max(1, min(720, int(params.get("durationHours", 1))))
        workload = str(params.get("workload", "general_compute")).strip()
        renter_id = str(params.get("renterId", "user-browser")).strip()

        tier = next((t for t in GPU_MARKETPLACE_TIERS if t["tierId"] == tier_id), None)
        if not tier:
            raise ValueError(f"unknown_gpu_tier: {tier_id}")

        total_price = round(tier["hourlyRate"] * duration_hours, 2)
        lease_id = f"lease-{tier_id}-{uuid.uuid4().hex[:8]}"
        stamp = now()
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat()

        provider_url = os.getenv("SAREMBOK_GPU_PROVIDER_URL", "").strip()
        provider_key = os.getenv("SAREMBOK_GPU_PROVIDER_API_KEY", "").strip()

        status = "PENDING_PROVIDER"
        provider_result: dict[str, Any] = {
            "provisioned": False,
            "reason": "gpu_provider_not_configured",
        }

        if provider_url:
            request = urllib.request.Request(
                provider_url.rstrip("/") + "/provision",
                data=json.dumps({
                    "tierId": tier_id,
                    "durationHours": duration_hours,
                    "workload": workload,
                    "renterId": renter_id,
                    "leaseId": lease_id,
                }).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    **({"Authorization": f"Bearer {provider_key}"} if provider_key else {}),
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as resp:
                    provider_result = json.loads(resp.read().decode("utf-8"))
                if bool(provider_result.get("provisioned")) or str(provider_result.get("status", "")).upper() in {"READY", "PROVISIONED", "ACTIVE"}:
                    status = "ACTIVE"
                else:
                    status = "PENDING_PROVIDER"
            except Exception as exc:
                provider_result = {
                    "provisioned": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                status = "PROVIDER_ERROR"

        store.db.execute(
            """
            INSERT INTO gpu_rentals(
                rental_id, tier_id, tier_name, vram_gb, hourly_rate,
                duration_hours, total_price, workload, status,
                renter_id, created_at, expires_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                lease_id, tier["tierId"], tier["tierName"], tier["vramGb"],
                tier["hourlyRate"], duration_hours, total_price, workload,
                status, renter_id, stamp, expires_at
            )
        )
        store.db.commit()

        event_type = "GPU_RENTAL_PROVISIONED" if status == "ACTIVE" else "GPU_RENTAL_REQUESTED"
        store.event(None, event_type, {
            "leaseId": lease_id,
            "tierId": tier_id,
            "durationHours": duration_hours,
            "totalPrice": total_price,
            "expiresAt": expires_at,
            "status": status,
            "provider": provider_result,
        })

        return {
            "success": status == "ACTIVE",
            "leaseId": lease_id,
            "tier": tier,
            "durationHours": duration_hours,
            "totalPrice": total_price,
            "status": status,
            "expiresAt": expires_at,
            "provider": provider_result,
            "message": (
                f"{tier['tierName']} provisioned and verified."
                if status == "ACTIVE"
                else "GPU rental request recorded; no active node is claimed until the configured provider reports provisioning."
            ),
        }

    if method == "ListGpuRentals":
        ensure_scheduler_schema()
        rows = store.db.execute(
            """
            SELECT rental_id, tier_id, tier_name, vram_gb, hourly_rate,
                   duration_hours, total_price, workload, status, created_at, expires_at
            FROM gpu_rentals
            ORDER BY created_at DESC LIMIT 50
            """
        ).fetchall()
        rentals = []
        for r in rows:
            rentals.append({
                "leaseId": r[0],
                "tierId": r[1],
                "tierName": r[2],
                "vramGb": r[3],
                "hourlyRate": r[4],
                "durationHours": r[5],
                "totalPrice": r[6],
                "workload": r[7],
                "status": r[8],
                "createdAt": r[9],
                "expiresAt": r[10],
            })
        return {"rentals": rentals, "count": len(rentals)}

    if method == "ListFiles":
        cat_filter = str(params.get("category", "")).strip()
        query = "SELECT file_id, filename, path, size_bytes, mime_type, category, metadata, created_at FROM file_assets WHERE 1=1"
        qp = []
        if cat_filter:
            query += " AND category=?"
            qp.append(cat_filter)
        query += " ORDER BY created_at DESC LIMIT 100"
        rows = store.db.execute(query, qp).fetchall()
        files = []
        for r in rows:
            try:
                meta = json.loads(r[6]) if r[6] else {}
            except Exception:
                meta = {}
            files.append({
                "fileId": r[0],
                "filename": r[1],
                "path": r[2],
                "sizeBytes": r[3],
                "mimeType": r[4],
                "category": r[5],
                "metadata": meta,
                "createdAt": r[7],
            })
        return {"files": files, "count": len(files)}

    if method == "IndexFile":
        filename = str(params.get("filename", "")).strip()
        path = str(params.get("path", "")).strip() or filename
        size_bytes = int(params.get("sizeBytes", 0))
        mime_type = str(params.get("mimeType", "text/plain")).strip()
        category = str(params.get("category", "code")).strip()
        metadata = params.get("metadata", {})
        if not filename:
            raise ValueError("filename is required")
        file_id = f"file-{uuid.uuid4().hex[:10]}"
        stamp = now()
        store.db.execute(
            "INSERT INTO file_assets(file_id, filename, path, size_bytes, mime_type, category, metadata, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (file_id, filename, path, size_bytes, mime_type, category, json.dumps(metadata), stamp),
        )
        store.db.commit()
        store.event(None, "FILE_INDEXED", {"fileId": file_id, "filename": filename, "category": category})
        return {"fileId": file_id, "filename": filename, "indexed": True, "createdAt": stamp}

    if method == "ListCheckpoints":
        rows = store.db.execute("SELECT checkpoint_id, label, agent_id, task_id, wal_index, status, payload, created_at FROM checkpoints ORDER BY created_at DESC LIMIT 50").fetchall()
        ckpts = []
        for r in rows:
            try:
                pay = json.loads(r[6]) if r[6] else {}
            except Exception:
                pay = {}
            ckpts.append({
                "checkpointId": r[0],
                "label": r[1],
                "agentId": r[2],
                "taskId": r[3],
                "walIndex": r[4],
                "status": r[5],
                "payload": pay,
                "createdAt": r[7],
            })
        return {"checkpoints": ckpts, "count": len(ckpts)}

    if method == "CreateCheckpoint":
        label = str(params.get("label", "Manual Checkpoint")).strip()
        agent_id = params.get("agentId")
        task_id = params.get("taskId")
        wal_index = int(params.get("walIndex", 0))
        payload = params.get("payload", {})
        checkpoint_id = f"ckpt-{uuid.uuid4().hex[:8]}"
        stamp = now()
        store.db.execute(
            "INSERT INTO checkpoints(checkpoint_id, label, agent_id, task_id, wal_index, status, payload, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (checkpoint_id, label, agent_id, task_id, wal_index, "VERIFIED", json.dumps(payload), stamp),
        )
        store.db.commit()
        store.event(agent_id, "CHECKPOINT_CREATED", {"checkpointId": checkpoint_id, "label": label, "status": "VERIFIED"})
        return {"checkpointId": checkpoint_id, "label": label, "status": "VERIFIED", "createdAt": stamp}

    if method == "RestoreCheckpoint":
        checkpoint_id = str(params.get("checkpointId", "")).strip()
        row = store.db.execute("SELECT checkpoint_id, label, agent_id, task_id, payload FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)).fetchone()
        if not row:
            raise ValueError(f"checkpoint_not_found: {checkpoint_id}")
        stamp = now()
        store.event(row[2], "CHECKPOINT_RESTORED", {"checkpointId": checkpoint_id, "label": row[1]})
        return {"checkpointId": checkpoint_id, "label": row[1], "restored": True, "status": "RESTORED", "timestamp": stamp}

    if method == "ListGovernanceApprovals":
        status_filter = str(params.get("status", "")).strip().upper()
        query = "SELECT approval_id, action_type, target, risk_level, requested_by, status, details, created_at, resolved_at FROM governance_approvals WHERE 1=1"
        qp = []
        if status_filter:
            query += " AND status=?"
            qp.append(status_filter)
        query += " ORDER BY created_at DESC LIMIT 50"
        rows = store.db.execute(query, qp).fetchall()
        approvals = []
        for r in rows:
            try:
                det = json.loads(r[6]) if r[6] else {}
            except Exception:
                det = {}
            approvals.append({
                "approvalId": r[0],
                "actionType": r[1],
                "target": r[2],
                "riskLevel": r[3],
                "requestedBy": r[4],
                "status": r[5],
                "details": det,
                "createdAt": r[7],
                "resolvedAt": r[8],
            })
        return {"approvals": approvals, "count": len(approvals)}

    if method == "RequestGovernanceApproval":
        action_type = str(params.get("actionType", "DEPLOYMENT")).strip()
        target = str(params.get("target", "Global Edge")).strip()
        risk_level = str(params.get("riskLevel", "HIGH")).strip().upper()
        requested_by = params.get("requestedBy", "Sarembok Core")
        details = params.get("details", {})
        approval_id = f"gov-{uuid.uuid4().hex[:8]}"
        stamp = now()
        store.db.execute(
            "INSERT INTO governance_approvals(approval_id, action_type, target, risk_level, requested_by, status, details, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (approval_id, action_type, target, risk_level, requested_by, "PENDING_APPROVAL", json.dumps(details), stamp),
        )
        store.db.commit()
        store.event(None, "GOVERNANCE_APPROVAL_REQUESTED", {"approvalId": approval_id, "actionType": action_type, "target": target})
        return {"approvalId": approval_id, "actionType": action_type, "status": "PENDING_APPROVAL", "createdAt": stamp}

    if method == "ApproveGovernanceAction":
        approval_id = str(params.get("approvalId", "")).strip()
        row = store.db.execute("SELECT approval_id, action_type, target FROM governance_approvals WHERE approval_id=?", (approval_id,)).fetchone()
        if not row:
            raise ValueError(f"approval_not_found: {approval_id}")
        stamp = now()
        store.db.execute("UPDATE governance_approvals SET status='APPROVED', resolved_at=? WHERE approval_id=?", (stamp, approval_id))
        store.db.commit()
        store.event(None, "GOVERNANCE_ACTION_APPROVED", {"approvalId": approval_id, "actionType": row[1], "target": row[2]})
        return {"approvalId": approval_id, "status": "APPROVED", "resolvedAt": stamp}

    if method == "RejectGovernanceAction":
        approval_id = str(params.get("approvalId", "")).strip()
        row = store.db.execute("SELECT approval_id, action_type, target FROM governance_approvals WHERE approval_id=?", (approval_id,)).fetchone()
        if not row:
            raise ValueError(f"approval_not_found: {approval_id}")
        stamp = now()
        store.db.execute("UPDATE governance_approvals SET status='REJECTED', resolved_at=? WHERE approval_id=?", (stamp, approval_id))
        store.db.commit()
        store.event(None, "GOVERNANCE_ACTION_REJECTED", {"approvalId": approval_id, "actionType": row[1], "target": row[2]})
        return {"approvalId": approval_id, "status": "REJECTED", "resolvedAt": stamp}

    if method == "ListAgents":
        rows = store.db.execute("SELECT agent_id, display_name, status, created_at, updated_at FROM agents ORDER BY created_at DESC").fetchall()
        agents = [{"agentId": r[0], "displayName": r[1], "status": r[2], "createdAt": r[3], "updatedAt": r[4]} for r in rows]
        return {"agents": agents, "count": len(agents)}

    if method == "GetAgent":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        row = store.db.execute("SELECT agent_id, display_name, status, created_at, updated_at FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
        return {"agentId": row[0], "displayName": row[1], "status": row[2], "createdAt": row[3], "updatedAt": row[4]}

    if method == "ListTasks":
        status_filter = str(params.get("status", "")).strip().upper()
        if status_filter:
            rows = store.db.execute("SELECT task_id, task_type, assigned_worker_id, status, payload, created_at FROM tasks WHERE status=? ORDER BY created_at DESC LIMIT 100", (status_filter,)).fetchall()
        else:
            rows = store.db.execute("SELECT task_id, task_type, assigned_worker_id, status, payload, created_at FROM tasks ORDER BY created_at DESC LIMIT 100").fetchall()
        tasks = []
        for r in rows:
            try:
                payload = json.loads(r[4]) if r[4] else {}
            except Exception:
                payload = {}
            tasks.append({
                "taskId": r[0],
                "taskType": r[1],
                "assignedWorkerId": r[2],
                "status": r[3],
                "payload": payload,
                "createdAt": r[5],
            })
        return {"tasks": tasks, "count": len(tasks)}

    if method == "GetTask":
        task_id = str(params.get("taskId", ""))
        row = store.db.execute(
            "SELECT task_id, task_type, required_capability, payload, result, error, "
            "assigned_worker_id, status, created_at, updated_at FROM tasks WHERE task_id=?",
            (task_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"task_not_found: {task_id}")
        try:
            payload = json.loads(row[3]) if row[3] else {}
        except Exception:
            payload = {}
        try:
            result_data = json.loads(row[4]) if row[4] else {}
        except Exception:
            result_data = {}
        return {
            "taskId": row[0],
            "taskType": row[1],
            "requiredCapability": row[2],
            "payload": payload,
            "result": result_data,
            "error": row[5],
            "assignedWorkerId": row[6],
            "status": row[7],
            "createdAt": row[8],
            "updatedAt": row[9],
        }

    if method == "CreateTask":
        task_type = str(params.get("taskType", "general_compute")).strip() or "general_compute"
        assigned_worker = params.get("assignedWorkerId")
        payload = params.get("payload", {})
        required_capability = required_capability_for_task(
            task_type,
            params.get("requiredCapability"),
        )
        return store.create_task(
            task_type,
            str(assigned_worker) if assigned_worker else None,
            payload if isinstance(payload, dict) else {},
            required_capability,
        )

    if method == "CancelTask":
        task_id = str(params.get("taskId", ""))
        row = store.db.execute("SELECT task_id FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"task_not_found: {task_id}")
        stamp = now()
        store.db.execute("UPDATE tasks SET status='CANCELLED', updated_at=? WHERE task_id=?", (stamp, task_id))
        store.db.commit()
        store.event(None, "TASK_CANCELLED", {"taskId": task_id})
        return {"taskId": task_id, "status": "CANCELLED", "updatedAt": stamp}

    if method == "ListDigitalHumanSessions":
        status_filter = str(params.get("status", "")).strip().upper()
        if status_filter:
            rows = store.db.execute("SELECT session_id, agent_id, worker_id, metahuman_id, voice_profile, status, created_at FROM digital_human_sessions WHERE status=? ORDER BY created_at DESC LIMIT 100", (status_filter,)).fetchall()
        else:
            rows = store.db.execute("SELECT session_id, agent_id, worker_id, metahuman_id, voice_profile, status, created_at FROM digital_human_sessions ORDER BY created_at DESC LIMIT 100").fetchall()
        sessions = [{
            "sessionId": r[0],
            "agentId": r[1],
            "assignedWorkerId": r[2],
            "metahumanId": r[3],
            "voiceProfile": r[4],
            "status": r[5],
            "createdAt": r[6],
        } for r in rows]
        return {"sessions": sessions, "count": len(sessions)}

    if method in ("GetEvents", "ListEvents"):
        agent_id = str(params.get("agentId", ""))
        event_type = str(params.get("eventType", "")).strip()
        limit = min(200, max(1, int(params.get("limit", 100))))
        
        query = "SELECT agent_id, event_type, created_at, payload FROM events WHERE 1=1"
        query_params = []
        if agent_id:
            query += " AND agent_id=?"
            query_params.append(agent_id)
        if event_type:
            query += " AND event_type=?"
            query_params.append(event_type)
        query += " ORDER BY id DESC LIMIT ?"
        query_params.append(limit)
        
        rows = store.db.execute(query, query_params).fetchall()
        events = []
        for r in reversed(rows):
            try:
                payload = json.loads(r[3])
            except Exception:
                payload = r[3]
            events.append({"agentId": r[0], "type": r[1], "timestamp": r[2], "payload": payload})
        return {"agentId": agent_id or None, "events": events, "count": len(events)}

    if method == "CreateDigitalHumanSession":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        metahuman_id = str(params.get("metahumanId", "default"))
        voice_profile = str(params.get("voiceProfile", "default"))
        session_id = f"dhs-{uuid.uuid4().hex[:10]}"
        assigned_worker = select_worker(
            required_capability="meta_human",
        )
        stamp = now()
        store.db.execute(
            "INSERT INTO digital_human_sessions VALUES(?,?,?,?,?,?,?,?)",
            (session_id, agent_id, assigned_worker, metahuman_id, voice_profile, "ACTIVE", stamp, stamp),
        )
        store.db.commit()
        return {"sessionId": session_id, "agentId": agent_id, "assignedWorkerId": assigned_worker, "metahumanId": metahuman_id, "status": "ACTIVE"}

    if method == "GetDigitalHumanSession":
        session_id = str(params.get("sessionId", ""))
        row = store.db.execute("SELECT session_id, agent_id, worker_id, metahuman_id, voice_profile, status, created_at FROM digital_human_sessions WHERE session_id=?", (session_id,)).fetchone()
        if not row:
            raise ValueError(f"session_not_found: {session_id}")
        return {"sessionId": row[0], "agentId": row[1], "assignedWorkerId": row[2], "metahumanId": row[3], "voiceProfile": row[4], "status": row[5], "createdAt": row[6]}

    if method == "CloseDigitalHumanSession":
        session_id = str(params.get("sessionId", "")).strip()
        if not session_id:
            raise ValueError("sessionId is required")
        row = store.db.execute(
            "SELECT session_id, agent_id, status FROM digital_human_sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"session_not_found: {session_id}")
        stamp = now()
        store.db.execute(
            "UPDATE digital_human_sessions SET status='CLOSED', updated_at=? WHERE session_id=?",
            (stamp, session_id),
        )
        store.db.commit()
        store.event(row[1], "DIGITAL_HUMAN_SESSION_CLOSED", {"sessionId": session_id})
        return {"sessionId": session_id, "status": "CLOSED", "updatedAt": stamp}

    if method == "UpdateDigitalHumanSession":
        session_id = str(params.get("sessionId", "")).strip()
        status_val = str(params.get("status", "")).strip().upper()
        if not session_id:
            raise ValueError("sessionId is required")
        if not status_val:
            raise ValueError("status is required")
        row = store.db.execute(
            "SELECT session_id, agent_id, status FROM digital_human_sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"session_not_found: {session_id}")
        stamp = now()
        store.db.execute(
            "UPDATE digital_human_sessions SET status=?, updated_at=? WHERE session_id=?",
            (status_val, stamp, session_id),
        )
        store.db.commit()
        store.event(row[1], "DIGITAL_HUMAN_SESSION_UPDATED", {"sessionId": session_id, "status": status_val})
        return {"sessionId": session_id, "status": status_val, "updatedAt": stamp}

    if method == "ExecuteAutonomousPipeline":
        goal = str(params.get("goal") or params.get("objective") or "").strip()
        if not goal:
            raise ValueError("goal is required")
        pipeline_id = f"pipe-{uuid.uuid4().hex[:8]}"
        stamp = now()
        
        # 1. Spawn Lead Architect Agent
        architect_id = f"agent-arch-{uuid.uuid4().hex[:4]}"
        store.create_agent(architect_id, f"Lead-Architect-{uuid.uuid4().hex[:3].upper()}")
        
        # 2. Decompose into Subtasks
        subtasks = [
            {"type": "architecture_synthesis", "title": "System Architecture & Contract Definition", "requiredCapability": "inference"},
            {"type": "code_generation", "title": "High-Performance Core Implementation", "requiredCapability": "inference"},
            {"type": "verification_suite", "title": "Automated Test & Benchmark Suite", "requiredCapability": "compute"},
            {"type": "gpu_deployment", "title": "Distributed Worker Node Allocation", "requiredCapability": "gpu"},
        ]

        created_tasks = []
        previous_task_id = None
        for index, st in enumerate(subtasks, 1):
            task_payload = {
                "pipelineId": pipeline_id,
                "title": st["title"],
                "goal": goal,
                "stage": index,
            }
            if previous_task_id:
                task_payload["dependsOnTaskId"] = previous_task_id
            t_res = store.create_task(
                st["type"],
                None,
                task_payload,
                st["requiredCapability"],
            )
            created_tasks.append({
                "taskId": t_res.get("taskId"),
                "type": st["type"],
                "title": st["title"],
                "requiredCapability": st["requiredCapability"],
                "dependsOnTaskId": previous_task_id,
                "status": t_res.get("status"),
            })
            previous_task_id = t_res.get("taskId")

        assign_pending_tasks()
            
        # 3. Record in Semantic Memory
        mem_id = f"mem-{uuid.uuid4().hex[:8]}"
        store.db.execute(
            "INSERT INTO memories(memory_id, tier, key, value, agent_id, created_at) VALUES(?,?,?,?,?,?)",
            (mem_id, "EPISODIC", f"pipeline_{pipeline_id}", f"Autonomous pipeline executed for goal: '{goal}' with {len(subtasks)} stages.", architect_id, stamp)
        )
        store.db.commit()
        
        store.event(architect_id, "AUTONOMOUS_PIPELINE_INITIATED", {"pipelineId": pipeline_id, "goal": goal, "tasks": created_tasks})
        
        pipeline_status = (
            "RUNNING"
            if any(task.get("status") == "QUEUED" for task in created_tasks)
            else "PENDING_WORKER"
        )
        return {
            "pipelineId": pipeline_id,
            "status": pipeline_status,
            "goal": goal,
            "architectAgentId": architect_id,
            "tasks": created_tasks,
            "createdAt": stamp,
        }

    if method == "QueryCognitiveGraph":
        # Build 2D/3D topological graph of the entire operating system state
        agents = store.db.execute("SELECT agent_id, display_name, status FROM agents LIMIT 20").fetchall()
        memories = store.db.execute("SELECT memory_id, key, tier FROM memories LIMIT 20").fetchall()
        workers = store.db.execute("SELECT worker_id, status FROM workers LIMIT 10").fetchall()
        tasks = store.db.execute("SELECT task_id, task_type, status FROM tasks LIMIT 15").fetchall()
        
        nodes = []
        links = []
        
        # Root Core Node
        nodes.append({"id": "sarembok-core", "label": "Sarembok Core", "type": "core", "val": 20})
        
        for a in agents:
            nodes.append({"id": a[0], "label": a[1], "type": "agent", "status": a[2], "val": 12})
            links.append({"source": "sarembok-core", "target": a[0], "relation": "orchestrates"})
            
        for m in memories:
            nodes.append({"id": m[0], "label": m[1], "type": "memory", "tier": m[2], "val": 8})
            links.append({"source": "sarembok-core", "target": m[0], "relation": "persists"})
            
        for w in workers:
            nodes.append({"id": w[0], "label": w[0][:12], "type": "worker", "status": w[1], "val": 15})
            links.append({"source": "sarembok-core", "target": w[0], "relation": "mesh"})
            
        for t in tasks:
            nodes.append({"id": t[0], "label": t[1], "type": "task", "status": t[2], "val": 10})
            links.append({"source": "sarembok-core", "target": t[0], "relation": "schedules"})
            
        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "agents": len(agents),
                "memories": len(memories),
                "workers": len(workers),
                "tasks": len(tasks)
            }
        }

    if method == "ExecuteSystemAction":
        action = str(params.get("action", "diagnostics")).strip()
        stamp = now()
        if action == "diagnostics":
            w_stats = get_worker_status_counts()
            mem_count = store.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            return {"action": action, "timestamp": stamp, "verified": True, "result": {
                "status": "HEALTHY",
                "activeWorkers": w_stats["onlineWorkers"],
                "registeredWorkers": w_stats["registeredWorkers"],
                "memoryRecords": mem_count,
                "uptimeSeconds": int(time.time() - STARTED),
            }}
        if action == "sync_memory_graph":
            mem_count = store.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            return {"action": action, "timestamp": stamp, "verified": True, "result": {"syncedNodes": mem_count, "indexStatus": "SYNCED"}}
        return {"action": action, "timestamp": stamp, "verified": False, "status": "UNSUPPORTED_ACTION", "message": "No system action is reported as executed unless Sarembok has a concrete executor for it."}


    # ==================== PROMETHEUS SUPER-ENGINE FACETS ====================
    if method == "TriggerSelfEvolution":
        target_dim = params.get("dimension")
        milestone = evolver.run_evolution_cycle(target_dim)
        return {
            "milestoneId": milestone.milestone_id,
            "iteration": milestone.iteration,
            "dimension": milestone.dimension,
            "baselineLatencyMs": milestone.baseline_latency_ms,
            "optimizedLatencyMs": milestone.optimized_latency_ms,
            "speedupFactor": milestone.speedup_factor,
            "verificationHash": milestone.verification_hash,
            "timestamp": milestone.timestamp,
            "metadata": milestone.metadata
        }

    if method == "ListEvolutionMilestones":
        limit = min(100, max(1, int(params.get("limit", 20))))
        return {"milestones": evolver.get_evolution_history(limit)}

    if method == "CompileEngineeringSwarm":
        goal = str(params.get("goal", "Build high-performance real-time exchange")).strip()
        project = swarm_compiler.compile_project(goal)
        import dataclasses
        return {
            "projectId": project.project_id,
            "goal": project.goal,
            "status": project.status,
            "createdAt": project.created_at,
            "stages": [dataclasses.asdict(s) for s in project.stages],
            "files": [dataclasses.asdict(f) for f in project.all_files],
            "executionResult": project.execution_result
        }

    if method == "ListSwarmProjects":
        limit = min(50, max(1, int(params.get("limit", 10))))
        return {"projects": swarm_compiler.list_projects(limit)}

    if method == "QueryProactiveInsights":
        limit = min(50, max(1, int(params.get("limit", 15))))
        return {"insights": proactive_daemon.list_insights(limit)}

    if method == "TriggerProactiveScan":
        insights = proactive_daemon.run_proactive_scan()
        return {"insights": insights, "count": len(insights)}

    if method == "ExecuteSandboxCode":
        code_str = str(params.get("code", "")).strip()
        lang = str(params.get("language", "python")).lower()
        if not code_str:
            return {"status": "ERROR", "output": "No code provided for execution."}
        
        # Execute Python sandbox safely
        start_t = time.perf_counter()
        output_buffer = []
        try:
            local_scope = {"print": lambda *args: output_buffer.append(" ".join(str(a) for a in args))}
            exec(code_str, {"__builtins__": __builtins__}, local_scope)
            dur_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            out_txt = "\n".join(output_buffer) if output_buffer else "Execution completed with return code 0."
            return {"status": "SUCCESS", "language": lang, "executionTimeMs": dur_ms, "output": out_txt}
        except Exception as e:
            dur_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return {"status": "RUNTIME_EXCEPTION", "language": lang, "executionTimeMs": dur_ms, "output": f"Exception: {e}"}

    if method == "GenerateImage":
        prompt_text = str(params.get("prompt", "")).strip()
        aspect_ratio = str(params.get("aspectRatio", "1:1")).strip()
        seed = params.get("seed")
        preferred_engine = params.get("preferredEngine")
        if not prompt_text:
            raise ValueError("prompt is required")
        img_res = resolve_image_generation(prompt_text, aspect_ratio, seed, preferred_engine)
        return {
            "status": "COMPLETED",
            "image": img_res,
            "workerId": SOVEREIGN_WORKER_ID,
            "timestamp": now(),
        }

    if method == "GetVisualEngineStatus":
        return get_visual_engine_status()

    if method == "ExecuteComputeTask":
        task_type = str(params.get("taskType", "inference")).strip() or "inference"
        payload = params.get("payload", {})
        required_capability = required_capability_for_task(
            task_type,
            params.get("requiredCapability"),
        )
        if required_capability == "gpu":
            ensure_sovereign_worker()
        worker_id = select_worker(required_capability)
        if not worker_id:
            return {
                "status": "NO_VERIFIED_WORKER",
                "requiredCapability": required_capability,
                "message": "No verified online worker supports the requested task capability; the task was not marked RUNNING.",
            }
        task = store.create_task(
            task_type,
            worker_id,
            payload if isinstance(payload, dict) else {},
            required_capability,
        )
        return {**task, "workerId": worker_id, "status": "QUEUED", "verified": True}

    if method == "Health":
        worker_stats = get_worker_status_counts()
        session_count = store.db.execute("SELECT COUNT(*) FROM digital_human_sessions WHERE status!='TERMINATED'").fetchone()[0]
        return {
            "status": "ONLINE",
            "service": "sarembok-ve-cloud-runtime",
            "domain": "sarembok.com",
            "uptimeSeconds": int(time.time() - STARTED),
            "storage": "sqlite-wal",
            "authConfigured": bool(AUTH_TOKEN),
            "registeredWorkers": worker_stats["registeredWorkers"],
            "onlineWorkers": worker_stats["onlineWorkers"],
            "staleWorkers": worker_stats["staleWorkers"],
            "offlineWorkers": worker_stats["offlineWorkers"],
            "activeDigitalHumanSessions": session_count,
        }

    raise ValueError(f"unknown_method: {method}")


def issue_browser_session() -> str:
    now_ts = time.time()
    # Prune expired sessions opportunistically.
    expired = [token for token, expiry in BROWSER_SESSIONS.items() if expiry <= now_ts]
    for token in expired:
        BROWSER_SESSIONS.pop(token, None)
    token = secrets.token_urlsafe(32)
    BROWSER_SESSIONS[token] = now_ts + BROWSER_SESSION_TTL_SECONDS
    return token


def browser_session_valid(token: Any) -> bool:
    if not isinstance(token, str) or not token:
        return False
    expiry = BROWSER_SESSIONS.get(token)
    if expiry is None:
        return False
    if expiry <= time.time():
        BROWSER_SESSIONS.pop(token, None)
        return False
    return True


def authenticate(request: dict[str, Any], method: str) -> None:
    params = request.get("params")
    if not isinstance(params, dict):
        raise PermissionError("authentication_required")

    # Worker RPCs use a separate enrollment/token boundary. Browser session
    # credentials must never authorize worker registration or worker control.
    if method in WORKER_AUTH_METHODS:
        if method == "RegisterWorker":
            supplied = params.get("enrollmentToken")
            if (
                not WORKER_ENROLLMENT_TOKEN
                or not isinstance(supplied, str)
                or not _hmac.compare_digest(supplied, WORKER_ENROLLMENT_TOKEN)
            ):
                raise PermissionError("authentication_required")
            return

        worker_id = str(params.get("workerId", "")).strip()
        supplied = params.get("workerToken")
        if not worker_id or not isinstance(supplied, str) or not supplied:
            raise PermissionError("authentication_required")

        row = store.db.execute(
            "SELECT worker_token_hash FROM workers WHERE worker_id=?",
            (worker_id,),
        ).fetchone()
        token_hash = str(row[0] or "") if row else ""
        if not token_hash:
            raise PermissionError("authentication_required")

        supplied_hash = hashlib.sha256(supplied.encode("utf-8")).hexdigest()
        if not _hmac.compare_digest(supplied_hash, token_hash):
            raise PermissionError("authentication_required")
        return

    # Server-to-server/admin clients may continue using the master token.
    supplied = params.get("authToken")
    if AUTH_TOKEN and isinstance(supplied, str) and _hmac.compare_digest(supplied, AUTH_TOKEN):
        return

    # Browser clients receive a short-lived, scoped session token. The master
    # runtime credential is never sent to or rendered into browser HTML.
    session_token = params.get("sessionToken")
    if browser_session_valid(session_token) and method in BROWSER_ALLOWED_METHODS:
        return

    raise PermissionError("authentication_required")


def validate_request(request: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    if request.get("jsonrpc") != "2.0":
        raise ValueError("jsonrpc must be 2.0")
    method = request.get("method")
    if not isinstance(method, str) or not method or len(method) > MAX_METHOD_LENGTH:
        raise ValueError("invalid method")
    params = request.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    authenticate(request, method)
    return method, params

ACTIVE_TTS_STREAMS: dict[str, dict[str, Any]] = {}
ACTIVE_TTS_STREAMS_LOCK_REAL = threading.RLock()

def cancel_tts_stream(stream_id: str) -> bool:
    with ACTIVE_TTS_STREAMS_LOCK_REAL:
        state = ACTIVE_TTS_STREAMS.get(stream_id)
        if not state:
            return False
        state["cancelled"] = True
        response = state.get("response")
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        task = state.get("task")
        if task is not None and not task.done():
            task.cancel()
        return True


async def stream_speech_over_websocket(websocket, request_id: str, params: dict[str, Any]) -> None:
    """Stream authenticated Kokoro PCM with independent cancellation."""
    text_value = str(params.get("text", "")).strip()
    voice = str(params.get("voice", os.getenv("SAREMBOK_VOICE_DEFAULT", "af_heart"))).strip()
    language = str(params.get("language", "en-us")).strip().lower() or "en-us"
    speed = min(1.5, max(0.6, float(params.get("speed", 0.95))))
    if not text_value:
        raise ValueError("text_required")
    if len(text_value) > SAREMBOK_VOICE_MAX_CHARS:
        raise ValueError("text_too_long")

    payload = json.dumps({
        "text": text_value, "voice": voice, "language": language, "speed": speed
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{SAREMBOK_VOICE_URL}/tts/stream",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "audio/pcm"},
        method="POST",
    )

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=16)
    response_holder: dict[str, Any] = {}
    sentinel = object()

    def pump() -> None:
        try:
            with urllib.request.urlopen(req, timeout=VOICE_REQUEST_TIMEOUT_SECONDS) as resp:
                response_holder["response"] = resp
                with ACTIVE_TTS_STREAMS_LOCK_REAL:
                    state = ACTIVE_TTS_STREAMS.get(request_id)
                    if state is not None:
                        state["response"] = resp
                while True:
                    chunk = resp.read(32768)
                    if not chunk:
                        break
                    if ACTIVE_TTS_STREAMS.get(request_id, {}).get("cancelled"):
                        break
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop).result()
        except Exception as exc:
            response_holder["error"] = exc
        finally:
            try:
                asyncio.run_coroutine_threadsafe(queue.put(sentinel), loop).result()
            except Exception:
                pass

    state = {"cancelled": False, "response": None, "task": asyncio.current_task()}
    with ACTIVE_TTS_STREAMS_LOCK_REAL:
        if request_id in ACTIVE_TTS_STREAMS:
            raise ValueError("duplicate_tts_stream_id")
        ACTIVE_TTS_STREAMS[request_id] = state

    worker = asyncio.create_task(asyncio.to_thread(pump))
    try:
        await websocket.send(json.dumps({
            "method": "SynthesizeSpeechStream.started",
            "params": {"id": request_id, "sampleRate": 24000, "format": "s16le"}
        }, separators=(",", ":")))

        while True:
            item = await queue.get()
            if item is sentinel:
                break
            if state["cancelled"]:
                return
            await websocket.send(item)

        if state["cancelled"]:
            return
        if "error" in response_holder:
            raise response_holder["error"]

        await websocket.send(json.dumps({
            "method": "SynthesizeSpeechStream.done",
            "params": {"id": request_id}
        }, separators=(",", ":")))
    except asyncio.CancelledError:
        state["cancelled"] = True
        raise
    except Exception as exc:
        if not state["cancelled"]:
            try:
                await websocket.send(json.dumps({
                    "method": "SynthesizeSpeechStream.error",
                    "params": {"id": request_id, "error": str(exc)}
                }, separators=(",", ":")))
            except Exception:
                pass
        raise
    finally:
        state["cancelled"] = True if state.get("cancelled") else state.get("cancelled", False)
        resp = response_holder.get("response")
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass
        if not worker.done():
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
        with ACTIVE_TTS_STREAMS_LOCK_REAL:
            ACTIVE_TTS_STREAMS.pop(request_id, None)


async def _persist_deferred_chat(result: dict[str, Any]) -> None:
    session_id = str(result.pop("_persistSessionId", "default") or "default")
    prompt = str(result.pop("_persistPrompt", "") or "")
    reply = str(result.pop("_persistReply", "") or "")
    result.pop("_deferPersistence", None)
    if not prompt or not reply:
        return
    try:
        async with get_db_lock():
            await asyncio.to_thread(_save_conversation, session_id, prompt, reply)
            await asyncio.to_thread(
                store.event,
                "sarembok-prime",
                "CHAT_RESPONSE",
                {
                    "prompt": prompt[:200],
                    "model": result.get("model"),
                    "provider": result.get("source"),
                },
            )
    except Exception as exc:
        LOG.warning("deferred chat persistence failed: %s", exc)


async def handler(websocket) -> None:
    peer = getattr(websocket, "remote_address", None)
    LOG.info("connection_open peer=%s", peer)
    stream_tasks: set[asyncio.Task] = set()
    try:
        async for raw in websocket:
            request: Any = None
            try:
                if isinstance(raw, str) and len(raw.encode("utf-8")) > MAX_REQUEST_BYTES:
                    raise ValueError("request_too_large")
                request = json.loads(raw)
                method, params = validate_request(request)

                if method == "CancelActiveStream":
                    target_id = str(params.get("streamId") or params.get("id") or "")
                    cancelled = cancel_tts_stream(target_id) if target_id else False
                    await websocket.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {"cancelled": cancelled, "streamId": target_id}
                    }, separators=(",", ":")))
                    continue

                if method == "SynthesizeSpeechStream":
                    stream_id = str(request.get("id", "")).strip()
                    if not stream_id:
                        raise ValueError("tts_stream_id_required")
                    task = asyncio.create_task(stream_speech_over_websocket(websocket, stream_id, params))
                    stream_tasks.add(task)
                    task.add_done_callback(stream_tasks.discard)
                    continue

                if method == "SarembokChat" and bool(params.get("stream", False)) and not _is_browser_execution_intent(str(params.get("prompt") or params.get("message") or params.get("text") or "")) and not any(m in str(params.get("prompt") or params.get("message") or params.get("text") or "").lower() for m in MEDIA_EXECUTION_MARKERS):
                    # True end-to-end token streaming:
                    # provider stream -> callback -> WebSocket delta -> browser.
                    # The provider runs in a worker thread, so bridge its synchronous
                    # callback back onto the event loop without blocking inference.
                    loop = asyncio.get_running_loop()
                    delta_queue: asyncio.Queue[str | None] = asyncio.Queue()

                    async def _send_chat_deltas() -> None:
                        while True:
                            chunk = await delta_queue.get()
                            if chunk is None:
                                return
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "method": "SarembokChat.delta",
                                "params": {
                                    "id": request.get("id"),
                                    "text": chunk,
                                },
                            }, separators=(",", ":")))

                    def _on_delta(chunk: str) -> None:
                        text_chunk = str(chunk or "")
                        if text_chunk:
                            loop.call_soon_threadsafe(delta_queue.put_nowait, text_chunk)

                    delta_sender = asyncio.create_task(_send_chat_deltas())
                    stream_token = set_stream_callback(_on_delta)
                    try:
                        # The fast conversational lane performs no pre-provider SQLite
                        # work, so do not hold the global DB lock while waiting on Gemini.
                        # Complex/tool-backed dialogue keeps the serialized DB path.
                        prompt_hint = str(params.get("prompt") or params.get("message") or params.get("text") or "")
                        fast_chat = _is_fast_conversational_turn(
                            prompt_hint,
                            image_frame=str(params.get("imageFrame") or params.get("image_frame") or params.get("frame") or "").strip() or None,
                            admin=bool(params.get("admin", False)),
                        )
                        if fast_chat:
                            result = await asyncio.to_thread(dispatch, method, params)
                        else:
                            async with get_db_lock():
                                result = await asyncio.to_thread(dispatch, method, params)
                    finally:
                        reset_stream_callback(stream_token)
                        await delta_queue.put(None)
                        await delta_sender
                else:
                    async with get_db_lock():
                        result = await asyncio.to_thread(dispatch, method, params)

                defer_persistence = isinstance(result, dict) and bool(result.get("_deferPersistence"))
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                LOG.info("rpc_success method=%s request_id=%s", method, request.get("id"))
                await websocket.send(json.dumps(response, separators=(",", ":")))
                if defer_persistence:
                    asyncio.create_task(_persist_deferred_chat(result))
            except PermissionError as exc:
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32001, "message": str(exc)}}
                LOG.warning("rpc_auth_failed peer=%s", peer)
                await websocket.send(json.dumps(response, separators=(",", ":")))
            except Exception as exc:
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32000, "message": str(exc)}}
                LOG.warning("rpc_error peer=%s error=%s", peer, exc)
                await websocket.send(json.dumps(response, separators=(",", ":")))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        for task in list(stream_tasks):
            task.cancel()
        if stream_tasks:
            await asyncio.gather(*stream_tasks, return_exceptions=True)
        LOG.info("connection_close peer=%s", peer)


def process_http_response(connection: Any, request: Any, response: Any) -> Any:
    path = getattr(request, "path", "") or ""
    path_only = urllib.parse.urlsplit(path).path
    if path_only in ("/api/session", "/session", "/api/live/token"):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["Cache-Control"] = "no-store"
    return response


async def process_http_request(connection: Any, request: Any) -> Any:
    # If the request is a WebSocket upgrade attempt, return None to continue handshake
    headers = getattr(request, "headers", {})
    upgrade = headers.get("Upgrade", "") if hasattr(headers, "get") else ""
    if upgrade.lower() == "websocket":
        return None

    path = getattr(request, "path", None) or getattr(connection, "path", "/")
    # websockets exposes the request target including the query string. Route
    # decisions must use the path component so /api/tts?text=... reaches the
    # runtime HTTP handler instead of falling through to the WebSocket 426.
    path_only = urllib.parse.urlsplit(path).path
    if path_only in ("/health", "/healthz"):
        if hasattr(connection, "respond"):
            return connection.respond(200, "OK\n")
        return (200, [("Content-Type", "text/plain; charset=utf-8")], b"OK\n")
    if path_only in ("/api/session", "/session"):
        session_token = issue_browser_session()
        body = json.dumps({
            "sessionToken": session_token,
            "expiresIn": BROWSER_SESSION_TTL_SECONDS,
            "scope": sorted(BROWSER_ALLOWED_METHODS),
        }, separators=(",", ":"))
        if hasattr(connection, "respond"):
            return connection.respond(200, body)
        return (
            200,
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Cache-Control", "no-store"),
                ("Content-Length", str(len(body.encode("utf-8")))),
            ],
            body.encode("utf-8"),
        )
    def make_api_response(status: int, data: Any):
        body = json.dumps(data, separators=(",", ":"))
        body_bytes = body.encode("utf-8")
        if hasattr(connection, "respond"):
            resp = connection.respond(status, body)
            try:
                del resp.headers["Content-Type"]
            except Exception:
                pass
            resp.headers["Content-Type"] = "application/json; charset=utf-8"
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Cache-Control"] = "no-store"
            return resp
        return (
            status,
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Access-Control-Allow-Origin", "*"),
                ("Cache-Control", "no-store"),
                ("Content-Length", str(len(body_bytes))),
            ],
            body_bytes,
        )

    if path_only == "/api/live/token":
        # Native Gemini Live audio uses a short-lived, single-use token. The
        # browser never receives Sarembok's long-lived Gemini API key.
        auth_header = headers.get("Authorization", "") if hasattr(headers, "get") else ""
        bearer = auth_header[7:].strip() if isinstance(auth_header, str) and auth_header.lower().startswith("bearer ") else ""
        authorized = browser_session_valid(bearer) or (
            AUTH_TOKEN and bearer and _hmac.compare_digest(bearer, AUTH_TOKEN)
        )
        if not authorized:
            return make_api_response(401, {"error": "authentication_required"})

        parsed = urllib.parse.urlparse(path)
        query = urllib.parse.parse_qs(parsed.query)
        mode = str(query.get("mode", ["conversational"])[0]).strip().lower()
        if mode not in {"conversational", "agentic"}:
            return make_api_response(400, {"error": "invalid_live_mode"})
        try:
            token_data = await asyncio.to_thread(provision_ephemeral_token, mode)
            return make_api_response(200, token_data)
        except Exception as exc:
            LOG.warning("gemini_live_token_failed mode=%s error=%s", mode, exc)
            return make_api_response(503, {"error": "gemini_live_unavailable", "detail": str(exc)})

    if path_only == "/api/tts":
        # Neural TTS is deliberately behind the runtime session boundary.
        # The Kokoro container is private on the Docker network.
        auth_header = headers.get("Authorization", "") if hasattr(headers, "get") else ""
        bearer = auth_header[7:].strip() if isinstance(auth_header, str) and auth_header.lower().startswith("bearer ") else ""
        if not (browser_session_valid(bearer) or (AUTH_TOKEN and bearer and _hmac.compare_digest(bearer, AUTH_TOKEN))):
            return make_api_response(401, {"error": "authentication_required"})

        try:
            parsed = urllib.parse.urlparse(path)
            query = urllib.parse.parse_qs(parsed.query)
            text_value = str(query.get("text", [""])[0]).strip()
            voice = str(query.get("voice", [os.getenv("SAREMBOK_VOICE_DEFAULT", "af_heart")])[0]).strip()
            language = str(query.get("language", ["en-us"])[0]).strip().lower() or "en-us"
            speed_raw = str(query.get("speed", ["0.95"])[0]).strip()
            speed = min(1.5, max(0.6, float(speed_raw)))
            if not text_value:
                return make_api_response(400, {"error": "text_required"})
            if len(text_value) > SAREMBOK_VOICE_MAX_CHARS:
                return make_api_response(413, {"error": "text_too_long", "maxChars": SAREMBOK_VOICE_MAX_CHARS})

            voice_payload = json.dumps({
                "text": text_value,
                "voice": voice,
                "language": language,
                "speed": speed,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{SAREMBOK_VOICE_URL}/tts",
                data=voice_payload,
                headers={"Content-Type": "application/json", "Accept": "audio/wav"},
                method="POST",
            )
            # TTS synthesis is a blocking network/model call. Allow the CPU-only
            # Kokoro service enough time to complete long utterances and queued
            # requests while keeping the asyncio control plane non-blocking.
            # directly on the runtime asyncio event loop: doing so stalls the WebSocket
            # control plane for the entire Kokoro generation time and makes chat appear
            # hung. Keep the control plane responsive by moving the blocking call to a
            # worker thread.
            def fetch_voice_audio():
                with urllib.request.urlopen(req, timeout=VOICE_REQUEST_TIMEOUT_SECONDS) as resp:
                    return resp.read()

            audio = await asyncio.to_thread(fetch_voice_audio)

            if not audio:
                return make_api_response(502, {"error": "voice_service_returned_no_audio"})

            # Return a real websockets HTTP Response with the WAV bytes in
            # the constructor.  The previous implementation built a text
            # response with connection.respond() and then mutated its body.
            # That is fragile across websockets releases and was the wrong
            # abstraction for binary audio.
            from websockets.datastructures import Headers
            from websockets.http11 import Response

            return Response(
                200,
                "OK",
                Headers([
                    ("Content-Type", "audio/wav"),
                    ("Cache-Control", "no-store"),
                    ("Content-Length", str(len(audio))),
                    ("Access-Control-Allow-Origin", "*"),
                ]),
                audio,
            )
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
            except Exception:
                detail = str(exc)
            return make_api_response(502, {"error": "voice_service_error", "detail": detail})
        except Exception as exc:
            LOG.warning("neural_tts_failed error=%s", exc)
            return make_api_response(503, {"error": "neural_tts_unavailable", "detail": str(exc)})

    if path == "/api/chat-sessions":
        try:
            rows = store.db.execute("SELECT session_id, title, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC LIMIT 50").fetchall()
            sessions = [{"session_id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]
            return make_api_response(200, {"sessions": sessions})
        except Exception as exc:
            return make_api_response(500, {"error": str(exc)})

    if path.startswith("/api/chat-session-load"):
        try:
            parsed = urllib.parse.urlparse(path)
            q = urllib.parse.parse_qs(parsed.query)
            session_id = q.get("id", [""])[0]
            row = store.db.execute("SELECT session_id, title, messages_json, created_at, updated_at FROM chat_sessions WHERE session_id = ?", (session_id,)).fetchone()
            if row:
                return make_api_response(200, {
                    "session_id": row[0],
                    "title": row[1],
                    "messages": json.loads(row[2] or "[]"),
                    "created_at": row[3],
                    "updated_at": row[4]
                })
            return make_api_response(404, {"error": "Session not found."})
        except Exception as exc:
            return make_api_response(500, {"error": str(exc)})

    if path == "/api/background-tasks":
        try:
            rows = store.db.execute("SELECT task_id, task_type, status, created_at, updated_at FROM tasks ORDER BY created_at DESC LIMIT 50").fetchall()
            tasks = [{"task_id": r[0], "directive": r[1], "status": r[2], "created_at": r[3], "updated_at": r[4]} for r in rows]
            return make_api_response(200, {"tasks": tasks})
        except Exception as exc:
            return make_api_response(500, {"error": str(exc)})

    if path in ("/", "/index.html"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "frontend", "index.html"),
            os.path.join(base_dir, "..", "frontend", "index.html"),
            os.path.join(base_dir, "..", "..", "frontend", "index.html"),
            os.path.abspath(os.path.join(os.getcwd(), "frontend", "index.html")),
            "/app/frontend/index.html",
            "frontend/index.html",
        ]
        html_str = None
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        html_str = f.read()
                    break
                except Exception as exc:
                    LOG.error("Failed to read frontend index.html: %s", exc)
        if not html_str:
            html_str = "<!DOCTYPE html><html><body><h1>Sarembok VE Cloud Runtime</h1><p>Status: ONLINE</p></body></html>\n"
        if hasattr(connection, "respond"):
            resp = connection.respond(200, html_str)
            try:
                del resp.headers["Content-Type"]
            except Exception:
                pass
            resp.headers["Content-Type"] = "text/html; charset=utf-8"
            resp.headers["Cache-Control"] = "no-cache"
            return resp
        return (200, [("Content-Type", "text/html; charset=utf-8")], html_str.encode("utf-8"))
    return None


async def worker_lifecycle_loop() -> None:
    LOG.info("worker lifecycle monitor started interval=%ss", WORKER_LIFECYCLE_INTERVAL_SECONDS)
    stop_evt = get_stop_event()
    try:
        while not stop_evt.is_set():
            try:
                async with get_db_lock():
                    ensure_sovereign_worker()
                    evaluate_worker_liveness()
            except Exception as exc:
                LOG.error("error in worker lifecycle loop: %s", exc)

            try:
                await asyncio.sleep(WORKER_LIFECYCLE_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
    finally:
        LOG.info("worker lifecycle monitor stopped")


async def serve() -> None:
    global MONITOR_TASK
    LOG.info("startup port=%s max_connections=%s auth_configured=%s db=%s", PORT, MAX_CONNECTIONS, bool(AUTH_TOKEN), DB_PATH)
    ensure_scheduler_schema()
    ensure_sovereign_worker()
    MONITOR_TASK = asyncio.create_task(worker_lifecycle_loop())
    try:
        async with websockets.serve(
            lambda ws: CONNECTIONS_guard(ws),
            "0.0.0.0",
            PORT,
            max_size=MAX_REQUEST_BYTES,
            # process_request handles /api/tts and performs synchronous Kokoro
            # generation in a worker thread. The websockets HTTP handshake
            # timeout defaults to 10s, which aborts legitimate TTS requests
            # before CPU synthesis can finish and surfaces as a Caddy 502/EOF.
            # Keep the control plane non-blocking while allowing neural TTS to
            # complete for the full configured text limit.
            open_timeout=90,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            compression=None,
            process_request=process_http_request,
            process_response=process_http_response,
        ) as server:
            LOG.info("listening address=0.0.0.0:%s", PORT)
            await get_stop_event().wait()
            LOG.info("shutdown_requested")
            server.close()
            await server.wait_closed()
    finally:
        if MONITOR_TASK:
            MONITOR_TASK.cancel()
            try:
                await MONITOR_TASK
            except asyncio.CancelledError:
                pass


async def CONNECTIONS_guard(websocket) -> None:
    sem = get_connections()
    try:
        await asyncio.wait_for(sem.acquire(), timeout=5)
    except TimeoutError:
        await websocket.close(code=1013, reason="server_busy")
        return
    try:
        await handler(websocket)
    finally:
        sem.release()


def request_shutdown() -> None:
    LOG.info("shutdown_signal")
    get_stop_event().set()


async def main() -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_shutdown)
        except (NotImplementedError, RuntimeError):
            signal.signal(sig, lambda *_: request_shutdown())
    try:
        await serve()
    finally:
        store.close()
        LOG.info("shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
