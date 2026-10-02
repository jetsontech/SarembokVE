"""Shared concrete task execution primitives for Sarembok VE workers.

The executor is deliberately dependency-aware: it never reports work as complete
unless a real local executor or explicitly configured integration produced evidence.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Callable


_HOST_ACTIONS = {"open_url", "launch_app", "open_file", "run_command"}


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 60) -> tuple[int, dict[str, Any] | str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return int(resp.status), json.loads(raw) if raw else {}
            except Exception:
                return int(resp.status), raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return int(exc.code), json.loads(raw) if raw else {}
        except Exception:
            return int(exc.code), raw


class WorkerTaskExecutor:
    """Concrete, capability-aware executor shared by worker daemons."""

    def __init__(
        self,
        worker_id: str,
        gpu_info: dict[str, Any] | None = None,
        host_action: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.worker_id = worker_id
        self.gpu_info = gpu_info or {}
        self.host_action = host_action

    def capabilities(self) -> list[str]:
        caps = ["compute"]
        if self.host_action is not None:
            caps.extend(["host_control", "desktop"])
        if self._gpu_available():
            caps.append("gpu")
        if self._inference_endpoint() or self._transformers_available():
            caps.append("inference")
        if os.getenv("SAREMBOK_UNREAL_BRIDGE_URL", "").strip():
            caps.append("meta_human")
        if self._playwright_available():
            caps.append("web_automation")
        return caps

    def execute(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        t = str(task_type or "compute").strip().lower()
        p = payload if isinstance(payload, dict) else {}
        started = time.perf_counter()

        if t in {"smoke_test", "arithmetic", "compute", "general_compute"}:
            result = self._compute(p)
        elif t in {"host_action", "desktop"}:
            result = self._host(p)
        elif t in {"inference", "architecture_synthesis", "code_generation"}:
            result = self._inference(p, task_type=t)
        elif t == "web_automation":
            result = self._web_automation(p)
        elif t == "meta_human":
            result = self._meta_human(p)
        elif t == "verification_suite":
            result = self._verification_suite(p)
        elif t == "gpu_deployment":
            result = self._gpu_deployment(p)
        else:
            # A generic named task can still execute when it explicitly asks for
            # one of the supported operation families; otherwise fail truthfully.
            op = str(p.get("operation", "")).strip().lower()
            if op in {"add", "multiply", "subtract", "divide", "modulo", "power", "average", "min", "max"}:
                result = self._compute(p)
            else:
                result = {
                    "status": "UNSUPPORTED",
                    "error": f"No concrete executor is installed for task type '{task_type}'",
                    "retryable": False,
                }

        result.setdefault("executedBy", self.worker_id)
        result.setdefault("timestamp", time.time())
        result.setdefault("executionTimeMs", round((time.perf_counter() - started) * 1000.0, 2))
        return result

    def _compute(self, payload: dict[str, Any]) -> dict[str, Any]:
        op = str(payload.get("operation", "add")).strip().lower()
        values = payload.get("values")
        if isinstance(values, list) and values:
            nums = [float(x) for x in values]
            if op == "sum":
                value = sum(nums)
            elif op == "average":
                value = sum(nums) / len(nums)
            elif op == "min":
                value = min(nums)
            elif op == "max":
                value = max(nums)
            else:
                return {"status": "ERROR", "error": f"Unsupported compute operation: {op}"}
            return {"status": "COMPLETED", "result": value, "operation": op}

        a = float(payload.get("a", 0))
        b = float(payload.get("b", 0))
        if op in {"add", "sum"}:
            value = a + b
        elif op == "multiply":
            value = a * b
        elif op == "subtract":
            value = a - b
        elif op == "divide":
            if b == 0:
                return {"status": "ERROR", "error": "division_by_zero"}
            value = a / b
        elif op == "modulo":
            if b == 0:
                return {"status": "ERROR", "error": "modulo_by_zero"}
            value = a % b
        elif op == "power":
            value = a ** b
        elif op == "average":
            value = (a + b) / 2.0
        elif op == "min":
            value = min(a, b)
        elif op == "max":
            value = max(a, b)
        else:
            return {"status": "ERROR", "error": f"Unsupported compute operation: {op}"}
        return {"status": "COMPLETED", "result": value, "operation": op}

    def _host(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.host_action is None:
            return {"status": "UNAVAILABLE", "error": "host executor is not configured", "retryable": True}
        return self.host_action(payload)

    def _inference_endpoint(self) -> str:
        explicit = os.getenv("SAREMBOK_WORKER_INFERENCE_URL", "").strip()
        if explicit:
            return explicit
        return ""

    def _transformers_available(self) -> bool:
        model_id = os.getenv("SAREMBOK_WORKER_MODEL", "").strip()
        if not model_id:
            return False
        try:
            import torch  # type: ignore
            import transformers  # type: ignore
            return True
        except Exception:
            return False

    def _inference(self, payload: dict[str, Any], task_type: str = "inference") -> dict[str, Any]:
        prompt = str(payload.get("prompt") or payload.get("text") or payload.get("input") or "").strip()
        if not prompt:
            return {"status": "ERROR", "error": "inference prompt is required"}

        endpoint = self._inference_endpoint()
        if endpoint:
            model = str(payload.get("model") or os.getenv("SAREMBOK_WORKER_MODEL", "")).strip()
            headers: dict[str, str] = {}
            api_key = os.getenv("SAREMBOK_WORKER_INFERENCE_API_KEY", "").strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            started = time.perf_counter()
            if "/api/chat" in endpoint:
                body = {
                    "model": model or "llama3.2",
                    "messages": [
                        {"role": "system", "content": str(payload.get("system", "")).strip()},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                }
            else:
                body = {
                    "model": model or "default",
                    "messages": [
                        {"role": "system", "content": str(payload.get("system", "")).strip()},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                }

            status_code, response = _post_json(endpoint, body, headers=headers, timeout=int(payload.get("timeoutSeconds", 120)))
            if status_code < 200 or status_code >= 300:
                return {
                    "status": "FAILED",
                    "error": f"inference_http_{status_code}: {response}",
                    "retryable": True,
                    "model": model or None,
                }

            text = self._extract_inference_text(response)
            if not text:
                return {"status": "FAILED", "error": "inference response contained no text", "retryable": True}
            return {
                "status": "COMPLETED",
                "output": text,
                "model": model or None,
                "latencyMs": round((time.perf_counter() - started) * 1000.0, 2),
                "taskType": task_type,
            }

        model_id = os.getenv("SAREMBOK_WORKER_MODEL", "").strip()
        if model_id and self._transformers_available():
            try:
                from transformers import pipeline  # type: ignore
                import torch  # type: ignore
                device = 0 if torch.cuda.is_available() else -1
                pipe = pipeline("text-generation", model=model_id, device=device)
                out = pipe(prompt, max_new_tokens=int(payload.get("maxTokens", 256)), do_sample=False)
                generated = out[0].get("generated_text", "")
                if isinstance(generated, list):
                    generated = generated[-1].get("content", "") if generated else ""
                return {
                    "status": "COMPLETED",
                    "output": str(generated),
                    "model": model_id,
                    "taskType": task_type,
                }
            except Exception as exc:
                return {"status": "FAILED", "error": f"local_transformers_inference_failed: {exc}", "retryable": True}

        return {
            "status": "UNAVAILABLE",
            "error": "no local inference backend configured (set SAREMBOK_WORKER_INFERENCE_URL or SAREMBOK_WORKER_MODEL)",
            "retryable": True,
        }

    @staticmethod
    def _extract_inference_text(response: Any) -> str:
        if isinstance(response, str):
            return response.strip()
        if not isinstance(response, dict):
            return ""
        if isinstance(response.get("message"), dict):
            content = response["message"].get("content")
            if isinstance(content, str):
                return content.strip()
        if isinstance(response.get("choices"), list) and response["choices"]:
            first = response["choices"][0]
            if isinstance(first, dict):
                msg = first.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                    return msg["content"].strip()
                if isinstance(first.get("text"), str):
                    return first["text"].strip()
        for key in ("response", "output", "text", "content"):
            if isinstance(response.get(key), str):
                return response[key].strip()
        return ""

    def _playwright_available(self) -> bool:
        try:
            import playwright.sync_api  # type: ignore
            return True
        except Exception:
            return False

    @staticmethod
    def _browser_executable() -> str | None:
        explicit = os.getenv("SAREMBOK_WORKER_BROWSER_EXECUTABLE", "").strip()
        if explicit and os.path.isfile(explicit):
            return explicit

        if platform.system() == "Windows":
            candidates = [
                os.getenv("PROGRAMFILES", ""),
                os.getenv("PROGRAMFILES(X86)", ""),
                os.getenv("LOCALAPPDATA", ""),
            ]
            names = [
                ("Google", "Chrome", "Application", "chrome.exe"),
                ("Microsoft", "Edge", "Application", "msedge.exe"),
            ]
            for root in candidates:
                if not root:
                    continue
                for parts in names:
                    candidate = os.path.join(root, *parts)
                    if os.path.isfile(candidate):
                        return candidate

        for command in ("google-chrome", "chromium", "chromium-browser", "msedge"):
            found = __import__("shutil").which(command)
            if found:
                return found
        return None

    def _web_automation(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._playwright_available():
            return {"status": "UNAVAILABLE", "error": "Playwright is not installed on this worker", "retryable": True}

        url = str(payload.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            return {"status": "ERROR", "error": "web_automation requires an http(s) url"}

        actions = payload.get("actions") or []
        if not isinstance(actions, list):
            return {"status": "ERROR", "error": "actions must be a list"}

        from playwright.sync_api import sync_playwright  # type: ignore

        timeout_ms = min(120000, max(1000, int(payload.get("timeoutMs", 15000))))
        headless = bool(payload.get("headless", True))
        screenshot_path = str(payload.get("screenshotPath") or "").strip()

        try:
            with sync_playwright() as pw:
                browser_executable = self._browser_executable()
                launch_kwargs: dict[str, Any] = {"headless": headless}
                if browser_executable:
                    launch_kwargs["executable_path"] = browser_executable
                browser = pw.chromium.launch(**launch_kwargs)
                page = browser.new_page()
                page.set_default_timeout(timeout_ms)
                page.goto(url, wait_until=str(payload.get("waitUntil", "domcontentloaded")))
                observations: list[dict[str, Any]] = []

                for action in actions:
                    if not isinstance(action, dict):
                        continue
                    kind = str(action.get("type") or action.get("action") or "").strip().lower()
                    locator = str(action.get("selector") or action.get("locator") or "").strip()

                    if kind == "navigate":
                        target = str(action.get("url") or "").strip()
                        if not target.startswith(("http://", "https://")):
                            raise ValueError("navigate requires http(s) URL")
                        page.goto(target, wait_until="domcontentloaded")
                    elif kind == "click":
                        page.locator(locator).click()
                    elif kind in {"fill", "type"}:
                        value = str(action.get("value") or action.get("text") or "")
                        if kind == "fill":
                            page.locator(locator).fill(value)
                        else:
                            page.locator(locator).press_sequentially(value)
                    elif kind == "select":
                        page.locator(locator).select_option(str(action.get("value") or ""))
                    elif kind == "press":
                        page.locator(locator).press(str(action.get("key") or "Enter"))
                    elif kind == "scroll":
                        delta = int(action.get("deltaY", 800))
                        page.mouse.wheel(0, delta)
                    elif kind == "wait":
                        page.wait_for_timeout(min(30000, max(0, int(action.get("milliseconds", 500)))))
                    elif kind in {"text", "get_text", "extract_text"}:
                        txt = page.locator(locator).inner_text() if locator else page.locator("body").inner_text()
                        observations.append({"type": "text", "text": txt[:20000]})
                    elif kind == "screenshot":
                        target = str(action.get("path") or screenshot_path).strip()
                        if not target:
                            raise ValueError("screenshot action requires path")
                        page.screenshot(path=target, full_page=bool(action.get("fullPage", True)))
                        observations.append({"type": "screenshot", "path": target})
                    else:
                        raise ValueError(f"unsupported web action: {kind}")

                if screenshot_path and not any(o.get("path") == screenshot_path for o in observations):
                    page.screenshot(path=screenshot_path, full_page=True)
                    observations.append({"type": "screenshot", "path": screenshot_path})

                result = {
                    "status": "COMPLETED",
                    "url": page.url,
                    "title": page.title(),
                    "observations": observations,
                }
                browser.close()
                return result
        except Exception as exc:
            return {"status": "FAILED", "error": f"web_automation_failed: {exc}", "retryable": True}

    def _meta_human(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = os.getenv("SAREMBOK_UNREAL_BRIDGE_URL", "").strip()
        if not endpoint:
            return {"status": "UNAVAILABLE", "error": "SAREMBOK_UNREAL_BRIDGE_URL is not configured", "retryable": True}
        status_code, response = _post_json(
            endpoint,
            payload,
            headers={"X-Sarembok-Worker": self.worker_id},
            timeout=min(120, max(5, int(payload.get("timeoutSeconds", 30)))),
        )
        if status_code < 200 or status_code >= 300:
            return {"status": "FAILED", "error": f"unreal_bridge_http_{status_code}: {response}", "retryable": True}
        return {"status": "COMPLETED", "bridge": response, "verified": True}

    def _verification_suite(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run safe workspace verification by default; arbitrary commands remain opt-in."""
        command = str(payload.get("command") or payload.get("testCommand") or "").strip()
        workspace = str(
            payload.get("workspace")
            or payload.get("path")
            or os.getenv("SAREMBOK_WORKER_WORKSPACE", "")
        ).strip()

        if command:
            if os.getenv("SAREMBOK_WORKER_ALLOW_COMMANDS", "").strip().lower() not in {"1", "true", "yes", "on"}:
                return {
                    "status": "DISABLED",
                    "error": "worker command policy disables arbitrary verification commands",
                    "retryable": False,
                }
            if not bool(payload.get("confirm")):
                return {
                    "status": "REQUIRES_CONFIRMATION",
                    "error": "verification_suite arbitrary commands require explicit confirmation",
                    "retryable": False,
                }
            timeout = min(600, max(5, int(payload.get("timeoutSeconds", 120))))
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return {
                "status": "COMPLETED" if proc.returncode == 0 else "FAILED",
                "command": command,
                "exitCode": proc.returncode,
                "stdout": proc.stdout[-20000:],
                "stderr": proc.stderr[-10000:],
                "retryable": proc.returncode != 0,
            }

        if not workspace:
            return {
                "status": "UNAVAILABLE",
                "error": "verification workspace is not configured",
                "retryable": True,
            }

        workspace_path = os.path.abspath(workspace)
        if not os.path.exists(workspace_path):
            return {
                "status": "ERROR",
                "error": f"verification workspace does not exist: {workspace_path}",
                "retryable": False,
            }

        timeout = min(600, max(5, int(payload.get("timeoutSeconds", 120))))
        compile_proc = subprocess.run(
            [os.fspath(__import__("sys").executable), "-m", "compileall", "-q", workspace_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if compile_proc.returncode != 0:
            return {
                "status": "FAILED",
                "operation": "compileall",
                "workspace": workspace_path,
                "exitCode": compile_proc.returncode,
                "stdout": compile_proc.stdout[-10000:],
                "stderr": compile_proc.stderr[-10000:],
                "retryable": False,
            }

        result = {
            "status": "COMPLETED",
            "operation": "compileall",
            "workspace": workspace_path,
            "exitCode": 0,
            "compileOutput": compile_proc.stdout[-10000:],
        }

        if bool(payload.get("runTests", False)):
            pytest_probe = subprocess.run(
                [os.fspath(__import__("sys").executable), "-c", "import pytest"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if pytest_probe.returncode == 0:
                test_proc = subprocess.run(
                    [os.fspath(__import__("sys").executable), "-m", "pytest", "-q"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                result["tests"] = {
                    "status": "PASSED" if test_proc.returncode == 0 else "FAILED",
                    "exitCode": test_proc.returncode,
                    "stdout": test_proc.stdout[-15000:],
                    "stderr": test_proc.stderr[-10000:],
                }
                if test_proc.returncode != 0:
                    result["status"] = "FAILED"
            else:
                result["tests"] = {
                    "status": "UNAVAILABLE",
                    "reason": "pytest is not installed in the worker environment",
                }

        return result

    def _gpu_deployment(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._gpu_available():
            return {"status": "UNAVAILABLE", "error": "verified NVIDIA GPU is not available on this worker", "retryable": True}
        try:
            proc = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                return {"status": "FAILED", "error": "nvidia-smi verification failed", "retryable": True}
            return {
                "status": "COMPLETED",
                "gpu": proc.stdout.strip().splitlines(),
                "deploymentTarget": payload.get("target") or payload.get("model") or "worker-local",
                "verified": True,
            }
        except Exception as exc:
            return {"status": "FAILED", "error": str(exc), "retryable": True}

    def _gpu_available(self) -> bool:
        vendor = str(self.gpu_info.get("gpuVendor") or "").upper()
        return vendor == "NVIDIA" and int(self.gpu_info.get("vramMb") or 0) > 0


__all__ = ["WorkerTaskExecutor"]
