"""Sarembok VE Autonomous GPU/Compute Worker Client Daemon.

Handles full worker lifecycle:
1. Auto-detects GPU environment (NVIDIA RTX 4090 / CUDA / VRAM)
2. Connects to Sarembok Cloud Runtime WebSocket gateway
3. Registers capabilities ('compute', 'inference', 'meta_human')
4. Maintains active heartbeat loop
5. Polls/Claims assigned tasks, executes payloads, reports results
6. Resilient auto-reconnection and clean signal termination
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform
import signal
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import websockets

try:
    from worker_task_executor import WorkerTaskExecutor
except ImportError:
    from Deployment.cloud.worker_task_executor import WorkerTaskExecutor

logging.basicConfig(
    level=os.getenv("SAREMBOK_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
)
LOG = logging.getLogger("sarembok.worker")


def detect_gpu_info(tier: str | None = None) -> dict[str, Any]:
    """Detects physical GPU hardware or maps requested acceleration tier (RTX 4090 / A100 / T4)."""
    t = str(tier or "").strip().lower()
    if t in {"rtx4090", "4090"}:
        LOG.info("Provisioned Hardware Tier: NVIDIA GeForce RTX 4090 (24 GB VRAM, CUDA 12.4)")
        return {
            "gpuVendor": "NVIDIA",
            "gpuModel": "NVIDIA GeForce RTX 4090",
            "vramMb": 24576,
            "cudaVersion": "12.4",
            "availableMemoryMb": 22118,
            "supportedModels": ["meta-human-v1", "sarembok-reasoner-7b", "whisper-large-v3", "llama-3.3-70b-instruct"],
        }
    if t in {"a100", "a100-80gb"}:
        LOG.info("Provisioned Hardware Tier: NVIDIA A100-SXM4-80GB (80 GB VRAM, CUDA 12.4)")
        return {
            "gpuVendor": "NVIDIA",
            "gpuModel": "NVIDIA A100-SXM4-80GB",
            "vramMb": 81920,
            "cudaVersion": "12.4",
            "availableMemoryMb": 73728,
            "supportedModels": ["meta-human-v1", "sarembok-reasoner-70b", "whisper-large-v3", "deepseek-r1-distill"],
        }
    if t in {"t4", "tesla-t4"}:
        LOG.info("Provisioned Hardware Tier: NVIDIA Tesla T4 (16 GB VRAM, CUDA 12.2)")
        return {
            "gpuVendor": "NVIDIA",
            "gpuModel": "Tesla T4",
            "vramMb": 15360,
            "cudaVersion": "12.2",
            "availableMemoryMb": 13824,
            "supportedModels": ["meta-human-v1", "sarembok-reasoner-7b", "whisper-large-v3"],
        }

    # 1. Try PyTorch CUDA if installed (e.g. Google Colab Tesla T4, Kaggle, GPU server)
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            dev_name = torch.cuda.get_device_name(0)
            vram = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
            cuda_ver = str(torch.version.cuda or "12.0")
            LOG.info("Detected GPU via PyTorch: %s (%s MB VRAM, CUDA %s)", dev_name, vram, cuda_ver)
            return {
                "gpuVendor": "NVIDIA",
                "gpuModel": dev_name,
                "vramMb": vram,
                "cudaVersion": cuda_ver,
                "availableMemoryMb": int(vram * 0.9),
                "supportedModels": ["meta-human-v1", "sarembok-reasoner-7b", "whisper-large-v3", "llama-3.3-70b-instruct"],
            }
    except Exception:
        pass

    # 2. Try nvidia-smi CLI
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 2:
                dev_name = parts[0]
                vram = int(float(parts[1]))
                LOG.info("Detected GPU via nvidia-smi: %s (%s MB VRAM)", dev_name, vram)
                return {
                    "gpuVendor": "NVIDIA",
                    "gpuModel": dev_name,
                    "vramMb": vram,
                    "cudaVersion": "12.0",
                    "availableMemoryMb": int(vram * 0.85),
                    "supportedModels": ["meta-human-v1", "sarembok-reasoner-7b", "whisper-large-v3"],
                }
    except Exception:
        pass

    # 3. Truthful fallback: CPU Compute Engine (no fake GPU)
    proc = platform.processor() or "Host CPU Architecture"
    LOG.info("No physical NVIDIA GPU detected. Truthful worker registration: CPU (%s)", proc)
    return {
        "gpuVendor": "CPU",
        "gpuModel": f"CPU · {platform.machine().upper()} ({proc[:24].strip()})",
        "vramMb": 0,
        "cudaVersion": "N/A",
        "availableMemoryMb": 4096,
        "supportedModels": ["cpu-arithmetic", "general_compute", "web-automation"],
    }


class SarembokWorker:
    def __init__(
        self,
        ws_url: str,
        auth_token: str = "",
        enrollment_token: str = "",
        worker_id: str | None = None,
        capabilities: list[str] | None = None,
        heartbeat_interval: int = 15,
        poll_interval: int = 2,
        tier: str | None = None,
    ):
        raw_url = ws_url.strip()
        if not raw_url.startswith(("ws://", "wss://")):
            raw_url = f"wss://{raw_url}"
        parsed = urllib.parse.urlparse(raw_url)
        path = parsed.path
        if not path or path == "/":
            path = "/ws"
        netloc = parsed.netloc or parsed.path.split("/")[0]
        self.ws_url = f"{parsed.scheme}://{netloc}{path}"
        self.http_base = f"https://{netloc}" if parsed.scheme == "wss" else f"http://{netloc}"

        self.auth_token = auth_token
        self.enrollment_token = enrollment_token
        self.session_token = ""
        # A stable default ID lets the worker recover its own credential after
        # a process restart. Deployments that run multiple workers on one host
        # should supply distinct SAREMBOK_WORKER_ID values.
        self.worker_id = worker_id or f"worker-{platform.node().lower()}"
        self.worker_token_path = self._resolve_worker_token_path(self.worker_id)
        self.worker_token = self._load_persisted_worker_token()
        self.heartbeat_interval = heartbeat_interval
        self.poll_interval = poll_interval
        self.gpu_info = detect_gpu_info(tier=tier)
        self.executor = WorkerTaskExecutor(
            worker_id=self.worker_id,
            gpu_info=self.gpu_info,
            host_action=self.execute_host_action,
        )
        self.capabilities = capabilities or self.executor.capabilities()
        self.stop_event = asyncio.Event()
        self.req_counter = 0
        self.pending_rpcs: dict[str, asyncio.Future[Any]] = {}

    @staticmethod
    def _resolve_worker_token_path(worker_id: str) -> Path:
        configured = os.getenv("SAREMBOK_WORKER_TOKEN_FILE", "").strip()
        if configured:
            return Path(configured).expanduser()

        safe_id = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in worker_id)
        safe_id = safe_id.strip(".") or "worker"
        if os.name == "nt":
            base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
            base = base / "SarembokVE" / "WorkerCredentials"
        else:
            base = Path(os.getenv("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
            base = base / "sarembokve" / "worker-credentials"
        return base / f"{safe_id}.json"

    def _load_persisted_worker_token(self) -> str:
        try:
            payload = json.loads(self.worker_token_path.read_text(encoding="utf-8"))
            token = payload.get("workerToken") if isinstance(payload, dict) else None
            owner = payload.get("workerId") if isinstance(payload, dict) else None
            if owner == self.worker_id and isinstance(token, str) and token.strip():
                return token.strip()
        except (OSError, ValueError, TypeError):
            pass
        return ""

    def _persist_worker_token(self) -> None:
        if not self.worker_token:
            return
        temp_path: Path | None = None
        try:
            parent = self.worker_token_path.parent
            parent.mkdir(parents=True, exist_ok=True)
            configured_path = bool(os.getenv("SAREMBOK_WORKER_TOKEN_FILE", "").strip())
            if os.name != "nt" and not configured_path:
                os.chmod(parent, 0o700)

            payload = json.dumps(
                {"version": 1, "workerId": self.worker_id, "workerToken": self.worker_token},
                separators=(",", ":"),
            )
            temp_path = parent / (
                self.worker_token_path.name + f".tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}"
            )
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            fd = os.open(str(temp_path), flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.worker_token_path)
            temp_path = None
            if os.name != "nt":
                os.chmod(self.worker_token_path, 0o600)
        except Exception as exc:
            # Do not expose the token in logs or stop a newly enrolled worker just
            # because its local credential cache could not be written.
            LOG.warning(
                "Could not persist the worker credential; restart may require admin-authorized re-enrollment (%s)",
                type(exc).__name__,
            )
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def fetch_session_token(self) -> str:
        """Fetch a scoped session token from the cluster HTTP gateway."""
        try:
            req = urllib.request.Request(
                f"{self.http_base}/session",
                headers={"User-Agent": "Mozilla/5.0 (SarembokWorkerClient; Python)"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                token = str(data.get("sessionToken", "")).strip()
                if token:
                    LOG.info("Acquired dynamic session token from cluster gateway.")
                    self.session_token = token
                    return token
        except Exception as exc:
            LOG.debug("Session token fetch skipped/failed: %s", exc)
        return ""

    def stop(self) -> None:
        """Signals the worker daemon to stop all loops gracefully."""
        self.stop_event.set()

    def _rpc_request(self, method: str, params: dict[str, Any] | None = None) -> tuple[str, str]:
        self.req_counter += 1
        req_id = f"w-req-{self.req_counter}"
        p = dict(params or {})
        if method == "RegisterWorker":
            if self.worker_token:
                p["workerToken"] = self.worker_token
                p.setdefault("workerId", self.worker_id)
            else:
                if self.enrollment_token:
                    p["enrollmentToken"] = self.enrollment_token
                elif self.session_token:
                    p["sessionToken"] = self.session_token
            if self.auth_token:
                # This credential is a recovery path if the locally persisted
                # worker token is stale or has been lost. A valid worker token
                # still takes precedence and is not rotated by the server.
                p["authToken"] = self.auth_token
        elif self.worker_token:
            p["workerToken"] = self.worker_token
            p.setdefault("workerId", self.worker_id)
        elif self.session_token:
            p["sessionToken"] = self.session_token
        elif self.auth_token:
            p["authToken"] = self.auth_token
        payload = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": p})
        return req_id, payload

    async def _send_rpc(self, ws: websockets.ClientConnection, method: str, params: dict[str, Any] | None = None) -> Any:
        req_id, raw = self._rpc_request(method, params)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Any] = loop.create_future()
        self.pending_rpcs[req_id] = fut
        await ws.send(raw)
        try:
            return await asyncio.wait_for(fut, timeout=10.0)
        finally:
            self.pending_rpcs.pop(req_id, None)

    async def register(self, ws: websockets.ClientConnection) -> None:
        if not self.worker_token and not self.enrollment_token and not self.auth_token and not self.session_token:
            self.fetch_session_token()
        LOG.info("Registering worker '%s' (capabilities=%s)...", self.worker_id, self.capabilities)
        res = await self._send_rpc(
            ws,
            "RegisterWorker",
            {
                "workerId": self.worker_id,
                "capabilities": self.capabilities,
                "gpuVendor": self.gpu_info["gpuVendor"],
                "gpuModel": self.gpu_info["gpuModel"],
                "vramMb": self.gpu_info["vramMb"],
                "cudaVersion": self.gpu_info["cudaVersion"],
                "availableMemoryMb": self.gpu_info["availableMemoryMb"],
                "supportedModels": self.gpu_info["supportedModels"],
                "status": "ONLINE",
            },
        )
        issued_token = str(res.get("workerToken") or "").strip() if isinstance(res, dict) else ""
        if issued_token:
            self.worker_token = issued_token
        elif not self.worker_token:
            raise RuntimeError("Worker enrollment succeeded but no one-time workerToken was issued")
        # Cache the token so normal restarts use worker-scoped authority rather
        # than needing the bootstrap enrollment credential again.
        self._persist_worker_token()
        self.enrollment_token = ""
        LOG.info("Registration confirmed: status=%s workerTokenIssued=%s", res.get("status"), "yes" if self.worker_token else "no")

    async def verify_handshake(self) -> dict[str, Any]:
        """Perform a single roundtrip P2P WebSocket handshake verification for distributed fleet execution."""
        LOG.info("Probing WebSocket handshake at %s...", self.ws_url)
        worker_origin = os.getenv("SAREMBOK_WORKER_ORIGIN", "https://sarembok.com").strip() or None
        connect_kwargs = {"ping_interval": 20, "ping_timeout": 20}
        if worker_origin:
            connect_kwargs["origin"] = worker_origin

        loop = asyncio.get_running_loop()
        t0 = loop.time()
        async with websockets.connect(self.ws_url, **connect_kwargs) as ws:
            reader_task = asyncio.create_task(self.message_reader(ws))
            try:
                # 1. Register
                await self.register(ws)
                reg_time = loop.time() - t0

                # 2. Heartbeat check
                t_hb = loop.time()
                hb_res = await self._send_rpc(ws, "Heartbeat", {"workerId": self.worker_id, "status": "ONLINE"})
                hb_latency = (loop.time() - t_hb) * 1000.0

                # 3. Queue listening check
                t_list = loop.time()
                task_res = await self._send_rpc(ws, "ListTasks", {"status": "QUEUED", "workerId": self.worker_id})
                task_latency = (loop.time() - t_list) * 1000.0

                total_time = loop.time() - t0
                report = {
                    "status": "VERIFIED",
                    "handshake": "PASS",
                    "workerId": self.worker_id,
                    "workerTokenIssued": bool(self.worker_token),
                    "capabilities": self.capabilities,
                    "registrationTimeMs": round(reg_time * 1000.0, 2),
                    "heartbeatLatencyMs": round(hb_latency, 2),
                    "taskListLatencyMs": round(task_latency, 2),
                    "totalHandshakeTimeMs": round(total_time * 1000.0, 2),
                }
                LOG.info("Handshake successfully verified: %s", report)
                return report
            finally:
                reader_task.cancel()

    async def heartbeat_loop(self, ws: websockets.ClientConnection) -> None:
        LOG.info("Heartbeat loop started interval=%ss", self.heartbeat_interval)
        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(self.heartbeat_interval)
                res = await self._send_rpc(ws, "Heartbeat", {"workerId": self.worker_id, "status": "ONLINE"})
                LOG.debug("Heartbeat acknowledged: %s", res)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                LOG.warning("Heartbeat error: %s", exc)
                break

    def execute_task_payload(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a task through the shared concrete worker executor."""
        LOG.info("Executing task type='%s' payload=%s", task_type, payload)
        return self.executor.execute(task_type, payload)

    def execute_host_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a bounded action on the enrolled target machine and return evidence."""
        action = str(payload.get("action", "")).strip().lower()
        if action == "open_url":
            url = str(payload.get("url", "")).strip()
            if not url.startswith(("https://", "http://")):
                return {"status": "ERROR", "error": "open_url requires http(s) URL"}
            if platform.system() == "Windows":
                subprocess.Popen(["cmd", "/c", "start", "", url], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
            return {"status": "VERIFIED", "action": action, "url": url, "platform": platform.system()}

        if action == "launch_app":
            command = str(payload.get("command", "")).strip()
            args = payload.get("args") or []
            if not command:
                return {"status": "ERROR", "error": "launch_app requires command"}
            if not bool(payload.get("confirm")):
                return {"status": "REQUIRES_CONFIRMATION", "error": "explicit confirmation required"}
            proc = subprocess.Popen([command] + [str(x) for x in args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"status": "VERIFIED", "action": action, "command": command, "args": args, "pid": proc.pid, "platform": platform.system()}

        if action == "run_command":
            if not bool(payload.get("confirm")):
                return {"status": "REQUIRES_CONFIRMATION", "error": "explicit confirmation required"}
            if os.getenv("SAREMBOK_WORKER_ALLOW_COMMANDS", "").strip().lower() not in {"1", "true", "yes", "on"}:
                return {"status": "DISABLED", "error": "host command execution is disabled by worker policy"}
            command = str(payload.get("command", "")).strip()
            if not command:
                return {"status": "ERROR", "error": "run_command requires command"}
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=20, check=False)
            return {"status": "VERIFIED" if proc.returncode == 0 else "FAILED", "action": action, "command": command, "exitCode": proc.returncode, "stdout": proc.stdout[-5000:], "stderr": proc.stderr[-2000:], "platform": platform.system()}

        if action == "open_file":
            target = os.path.abspath(str(payload.get("path", "")).strip())
            if not target or not os.path.exists(target):
                return {"status": "ERROR", "error": "file_not_found", "path": target}
            if platform.system() == "Windows":
                os.startfile(target)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
            return {"status": "VERIFIED", "action": action, "path": target, "platform": platform.system()}

        return {"status": "ERROR", "error": "unsupported_host_action", "action": action}


    async def task_execution_loop(self, ws: websockets.ClientConnection, single_task_mode: bool = False) -> None:
        LOG.info("Task execution listener active (poll_interval=%ss)", self.poll_interval)
        while not self.stop_event.is_set():
            try:
                # 1. Check for tasks queued for this worker or pending matching capabilities
                task_list_queued = await self._send_rpc(ws, "ListTasks", {"status": "QUEUED", "workerId": self.worker_id})
                tasks_queued = task_list_queued.get("tasks", []) if isinstance(task_list_queued, dict) else []
                
                my_tasks = [t for t in tasks_queued if t.get("assignedWorkerId") == self.worker_id]

                if not my_tasks:
                    task_list_pending = await self._send_rpc(ws, "ListTasks", {"status": "PENDING_WORKER", "workerId": self.worker_id})
                    tasks_pending = task_list_pending.get("tasks", []) if isinstance(task_list_pending, dict) else []
                    my_tasks = [t for t in tasks_pending if (not t.get("assignedWorkerId") or t.get("assignedWorkerId") == self.worker_id) and (t.get("requiredCapability", "compute") in self.capabilities) and t.get("dependencyReady", True)]

                for t in my_tasks:
                    task_id = t["taskId"]
                    task_type = t.get("taskType", "compute")
                    payload = t.get("payload", {})
                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except Exception:
                            payload = {}

                    LOG.info("Found queued task '%s' (type=%s). Claiming...", task_id, task_type)
                    try:
                        claim_res = await self._send_rpc(ws, "ClaimTask", {"taskId": task_id, "workerId": self.worker_id})
                        LOG.info("Claimed task '%s': status=%s", task_id, claim_res.get("status"))

                        # Execute payload
                        result = await asyncio.to_thread(self.execute_task_payload, task_type, payload)

                        # Complete only real successes; non-executed actions are failed with evidence.
                        if result.get("status") in ("VERIFIED", "SUCCESS", "COMPLETED"):
                            comp_res = await self._send_rpc(ws, "CompleteTask", {
                                "taskId": task_id,
                                "workerId": self.worker_id,
                                "result": result,
                                "error": None,
                            })
                        else:
                            comp_res = await self._send_rpc(ws, "FailTask", {
                                "taskId": task_id,
                                "workerId": self.worker_id,
                                "error": str(result.get("error") or result.get("status") or "execution_not_completed"),
                                "retryable": False,
                            })
                        if single_task_mode:
                            LOG.info("Single task mode completed successfully.")
                            self.stop_event.set()
                            return
                    except Exception as task_exc:
                        LOG.error("Failed processing task '%s': %s", task_id, task_exc)
                        try:
                            await self._send_rpc(ws, "FailTask", {"taskId": task_id, "workerId": self.worker_id, "error": str(task_exc), "retryable": True})
                        except Exception:
                            pass

                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                LOG.warning("Task loop error: %s", exc)
                await asyncio.sleep(self.poll_interval)

    async def message_reader(self, ws: websockets.ClientConnection) -> None:
        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                    req_id = data.get("id")
                    if req_id and req_id in self.pending_rpcs:
                        fut = self.pending_rpcs[req_id]
                        if not fut.done():
                            if "error" in data and data["error"]:
                                fut.set_exception(RuntimeError(data["error"].get("message", "RPC Error")))
                            else:
                                fut.set_result(data.get("result"))
                except Exception as exc:
                    LOG.debug("Error decoding incoming frame: %s", exc)
        except websockets.exceptions.ConnectionClosed:
            LOG.info("Connection closed by peer.")

    async def run(self, single_task_mode: bool = False) -> None:
        retry_delay = 2
        while not self.stop_event.is_set():
            try:
                LOG.info("Connecting to Sarembok Cloud Runtime at %s...", self.ws_url)
                worker_origin = os.getenv("SAREMBOK_WORKER_ORIGIN", "https://sarembok.com").strip() or None
                connect_kwargs = {"ping_interval": 20, "ping_timeout": 20}
                if worker_origin:
                    connect_kwargs["origin"] = worker_origin
                async with websockets.connect(self.ws_url, **connect_kwargs) as ws:
                    LOG.info("Connected. Initializing worker...")
                    retry_delay = 2

                    reader_task = asyncio.create_task(self.message_reader(ws))
                    
                    # Register
                    await self.register(ws)

                    hb_task = asyncio.create_task(self.heartbeat_loop(ws))
                    task_task = asyncio.create_task(self.task_execution_loop(ws, single_task_mode=single_task_mode))

                    done, pending = await asyncio.wait(
                        [reader_task, hb_task, task_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    for p in pending:
                        p.cancel()

                    if single_task_mode and self.stop_event.is_set():
                        break

            except (ConnectionRefusedError, websockets.exceptions.WebSocketException, OSError) as exc:
                if self.stop_event.is_set():
                    break
                LOG.warning("Connection failure (%s). Retrying in %ss...", exc, retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)
            except Exception as exc:
                if self.stop_event.is_set():
                    break
                LOG.error("Unexpected worker error: %s", exc)
                await asyncio.sleep(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sarembok VE Compute Worker Daemon")
    parser.add_argument("--ws-url", default=os.getenv("SAREMBOK_WS_URL", "ws://127.0.0.1:9000"), help="WebSocket URL of Sarembok Cloud Runtime")
    parser.add_argument("--auth-token", default=os.getenv("SAREMBOK_AUTH_TOKEN", ""), help="Legacy operator token; normally unused for enrolled workers")
    parser.add_argument("--enrollment-token", default=os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", ""), help="One-time worker enrollment token issued by the Sarembok control plane")
    parser.add_argument("--worker-id", default=os.getenv("SAREMBOK_WORKER_ID", ""), help="Unique Worker ID")
    parser.add_argument("--heartbeat-interval", type=int, default=int(os.getenv("SAREMBOK_WORKER_HEARTBEAT_INTERVAL", "15")), help="Heartbeat interval in seconds")
    parser.add_argument("--poll-interval", type=int, default=2, help="Task poll interval in seconds")
    parser.add_argument("--once", action="store_true", help="Execute single task then exit (test mode)")
    parser.add_argument("--verify-handshake", action="store_true", help="Run one-time P2P handshake verification and exit")
    parser.add_argument("--tier", default=os.getenv("SAREMBOK_WORKER_TIER", ""), help="Target hardware accelerator tier (e.g. rtx4090, a100, t4, cpu)")
    return parser.parse_args()


async def main_async() -> None:
    args = parse_args()
    worker = SarembokWorker(
        ws_url=args.ws_url,
        auth_token=args.auth_token,
        enrollment_token=args.enrollment_token,
        worker_id=args.worker_id or None,
        heartbeat_interval=args.heartbeat_interval,
        poll_interval=args.poll_interval,
        tier=args.tier or None,
    )

    if args.verify_handshake:
        report = await worker.verify_handshake()
        print(json.dumps(report, indent=2))
        return

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: worker.stop_event.set())
        except (NotImplementedError, RuntimeError):
            pass

    await worker.run(single_task_mode=args.once)


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        LOG.info("Worker stopped by operator.")


if __name__ == "__main__":
    main()
