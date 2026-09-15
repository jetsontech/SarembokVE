"""SarembokVE provider routing, streaming, health, and latency telemetry.

The router treats model selection as a preference, not a single-provider
failure point. Provider-specific billing, authentication, model availability,
and rate-limit states are classified and cooled down so a bad upstream cannot
poison the whole request path.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any, Callable


TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}
_STREAM_CALLBACK: ContextVar[Callable[[str], None] | None] = ContextVar("sarembok_stream_callback", default=None)
logger = logging.getLogger("sarembok.provider_router")

# Process-wide health because ProviderRouter instances can be created per request.
_PROVIDER_COOLDOWNS: dict[str, float] = {}
_PROVIDER_STATUS: dict[str, dict[str, Any]] = {}
_PROVIDER_FAILURE_STREAK: dict[str, int] = {}


def set_stream_callback(callback: Callable[[str], None] | None):
    return _STREAM_CALLBACK.set(callback)


def reset_stream_callback(token) -> None:
    _STREAM_CALLBACK.reset(token)


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    model: str
    kind: str
    endpoint: str
    key: str


@dataclass
class ProviderResult:
    text: str
    provider: str
    model: str
    latency_ms: float
    attempts: int
    api: str
    usage: dict[str, Any] = field(default_factory=dict)
    ttft_ms: float | None = None


class ProviderStreamError(RuntimeError):
    def __init__(self, message: str, *, partial: bool = False):
        super().__init__(message)
        self.partial = partial


class ProviderRouter:
    MODEL_ALIASES: dict[str, str] = {
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "fast": "openai/gpt-4o-mini",
        "auto": "openrouter/auto",
        "openrouter-auto": "openrouter/auto",
        "gemini-flash": "~google/gemini-flash-latest",
        "gemini-3.6-flash": "google/gemini-3.6-flash",
        "gemini-2.5-flash": "google/gemini-2.5-flash",
        "llama-3.3-70b": "meta-llama/llama-3.3-70b-instruct",
        "reasoning": "openai/gpt-oss-120b",
        "gpt-oss-120b": "openai/gpt-oss-120b",
        "deepseek-v3": "deepseek/deepseek-chat",
        "deepseek": "deepseek/deepseek-chat",
        "qwen-2.5-coder": "qwen/qwen-2.5-coder-32b-instruct",
        "code": "qwen/qwen-2.5-coder-32b-instruct",
    }

    def __init__(self) -> None:
        self.provider_timeout = max(3, int(os.getenv("SAREMBOK_LLM_PROVIDER_TIMEOUT_SECONDS", "25")))
        self.total_timeout = max(5, int(os.getenv("SAREMBOK_LLM_TOTAL_TIMEOUT_SECONDS", "35")))
        self.gemini_api = os.getenv("SAREMBOK_GEMINI_API", "generatecontent").strip().lower()
        if self.gemini_api not in {"generatecontent", "interactions"}:
            self.gemini_api = "generatecontent"
        self.gemini_thinking = os.getenv("SAREMBOK_GEMINI_THINKING_LEVEL", "low").strip().lower()
        if self.gemini_thinking not in {"low", "medium", "high"}:
            self.gemini_thinking = "low"
        self.openrouter_reasoning = os.getenv("SAREMBOK_OPENROUTER_REASONING_EFFORT", "low").strip().lower()
        if self.openrouter_reasoning not in {"minimal", "low", "medium", "high", "xhigh"}:
            self.openrouter_reasoning = "low"
        self.max_output_tokens = max(64, int(os.getenv("SAREMBOK_LLM_MAX_OUTPUT_TOKENS", "8192")))
        self._history: deque[dict[str, Any]] = deque(maxlen=200)

    @staticmethod
    def _provider_available(name: str) -> bool:
        until = _PROVIDER_COOLDOWNS.get(name, 0.0)
        if until <= time.monotonic():
            _PROVIDER_COOLDOWNS.pop(name, None)
            status = _PROVIDER_STATUS.get(name)
            if status and status.get("state") not in {"healthy", "unknown"}:
                status["state"] = "ready"
                status["cooldownSeconds"] = 0
            return True
        return False

    @staticmethod
    def _set_provider_cooldown(name: str, seconds: float, *, state: str, reason: str = "") -> None:
        seconds = max(1.0, float(seconds))
        _PROVIDER_COOLDOWNS[name] = time.monotonic() + seconds
        _PROVIDER_STATUS[name] = {
            "state": state,
            "cooldownSeconds": round(seconds, 1),
            "reason": reason,
            "updatedAt": time.time(),
        }

    @staticmethod
    def _mark_success(name: str) -> None:
        _PROVIDER_FAILURE_STREAK[name] = 0
        _PROVIDER_STATUS[name] = {
            "state": "healthy",
            "cooldownSeconds": 0,
            "reason": "",
            "updatedAt": time.time(),
        }

    @staticmethod
    def _http_error_body(exc: urllib.error.HTTPError) -> str:
        try:
            raw = exc.read()
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return ""

    @staticmethod
    def _classify_http_error(body: str) -> str:
        lowered = body.lower()
        if any(marker in lowered for marker in ("more credits", "openrouter_credits", "insufficient credits", "billing")):
            return "billing_unavailable"
        if any(marker in lowered for marker in ("quota exceeded", "free_tier", "quota")):
            return "quota_exceeded"
        if "rate limit" in lowered or "too many requests" in lowered:
            return "rate_limited"
        if "no endpoints found" in lowered or "model" in lowered and "not found" in lowered:
            return "model_unavailable"
        return "http_error"

    @staticmethod
    def _retry_after(exc: urllib.error.HTTPError) -> float | None:
        try:
            value = exc.headers.get("Retry-After")
            if value:
                return max(1.0, float(value))
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    @staticmethod
    def _reset_seconds(exc: urllib.error.HTTPError) -> float | None:
        for key in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
            try:
                value = exc.headers.get(key)
                if not value:
                    continue
                text = str(value).strip().lower()
                if text.endswith("s"):
                    return max(1.0, float(text[:-1]))
                if text.endswith("m"):
                    return max(1.0, float(text[:-1]) * 60)
                return max(1.0, float(text))
            except (TypeError, ValueError, AttributeError):
                continue
        return None

    @staticmethod
    def _extract_openai(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI-compatible provider returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "".join(
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
        text = str(content).strip()
        finish_reason = choices[0].get("finish_reason")
        if not text:
            reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
            if reasoning and finish_reason != "length":
                text = str(reasoning).strip()
            else:
                raise RuntimeError(f"OpenAI-compatible provider returned empty content (finish_reason={finish_reason})")
        usage = dict(payload.get("usage") or {})
        if finish_reason:
            usage["_finish_reason"] = finish_reason
        return text, usage

    @staticmethod
    def _extract_gemini(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        parts: list[str] = []
        for step in payload.get("steps", []) or []:
            if step.get("type") != "model_output":
                continue
            for block in step.get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                    parts.append(str(block["text"]))
        if not parts:
            for candidate in payload.get("candidates", []) or []:
                for part in candidate.get("content", {}).get("parts", []) or []:
                    if isinstance(part, dict) and part.get("text"):
                        parts.append(str(part["text"]))
        if not parts:
            raise RuntimeError("Gemini returned no model output")
        return "".join(parts).strip(), dict(payload.get("usage") or payload.get("usageMetadata") or {})

    @staticmethod
    def _sse_events(response) -> Any:
        event_name = None
        data_lines: list[str] = []
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif not line:
                if data_lines:
                    raw_data = "\n".join(data_lines)
                    if raw_data == "[DONE]":
                        yield event_name or "done", None
                    else:
                        try:
                            yield event_name or "message", json.loads(raw_data)
                        except json.JSONDecodeError:
                            pass
                event_name = None
                data_lines = []
        if data_lines:
            raw_data = "\n".join(data_lines)
            if raw_data != "[DONE]":
                try:
                    yield event_name or "message", json.loads(raw_data)
                except json.JSONDecodeError:
                    pass

    def resolve_model_id(self, model_hint: str | None) -> str | None:
        if not model_hint:
            return None
        cleaned = model_hint.strip().lower()
        return self.MODEL_ALIASES.get(cleaned, model_hint.strip())

    @staticmethod
    def _is_openrouter_model(model: str | None) -> bool:
        if not model:
            return False
        return model.startswith(("google/", "~google/", "openai/", "meta-llama/", "deepseek/", "qwen/", "anthropic/", "openrouter/"))

    def configured(self, requested_model: str | None = None, dynamic_key: str | None = None) -> list[ProviderSpec]:
        result: dict[str, ProviderSpec] = {}
        target = self.resolve_model_id(requested_model)

        if dynamic_key:
            key = str(dynamic_key).strip()
            if key.startswith("sk-or-"):
                result["UserOpenRouter"] = ProviderSpec("UserOpenRouter", target or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"), "openai", "https://openrouter.ai/api/v1/chat/completions", key)
            elif key.startswith("AIza"):
                result["UserGemini"] = ProviderSpec("UserGemini", os.getenv("GEMINI_MODEL", "gemini-3.6-flash"), "gemini", "https://generativelanguage.googleapis.com/v1beta/generateContent", key)
            elif key.startswith("gsk_"):
                result["UserGroq"] = ProviderSpec("UserGroq", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), "openai", "https://api.groq.com/openai/v1/chat/completions", key)
            elif key.startswith("sk-"):
                result["UserOpenAI"] = ProviderSpec("UserOpenAI", os.getenv("LLM_MODEL", "gpt-5-mini"), "openai", "https://api.openai.com/v1/chat/completions", key)

        openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        custom_url = os.getenv("LLM_ENDPOINT_URL", "").strip()

        if openrouter_key:
            model = target if self._is_openrouter_model(target) else os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
            result["OpenRouter"] = ProviderSpec("OpenRouter", model, "openai", "https://openrouter.ai/api/v1/chat/completions", openrouter_key)
        if groq_key:
            result["Groq"] = ProviderSpec("Groq", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), "openai", "https://api.groq.com/openai/v1/chat/completions", groq_key)
        if gemini_key:
            result["Gemini"] = ProviderSpec("Gemini", os.getenv("GEMINI_MODEL", "gemini-3.6-flash"), "gemini", "https://generativelanguage.googleapis.com/v1beta/generateContent", gemini_key)
        if openai_key:
            result["OpenAI"] = ProviderSpec("OpenAI", os.getenv("LLM_MODEL", "gpt-5-mini"), "openai", "https://api.openai.com/v1/chat/completions", openai_key)
        if custom_url:
            result["Custom"] = ProviderSpec("Custom", os.getenv("LLM_MODEL", "llama-3.1-8b"), "openai", custom_url, os.getenv("LLM_API_KEY", "dummy"))

        configured_order = [x.strip() for x in os.getenv("SAREMBOK_PROVIDER_ORDER", "Groq,OpenRouter,Gemini,OpenAI,Custom").split(",") if x.strip()]
        ordered_names = [name for name in configured_order if name in result]

        # An explicit model preference gets first chance at its native provider;
        # if that provider is unavailable, the normal cross-provider chain remains.
        if target and self._is_openrouter_model(target) and "OpenRouter" in ordered_names:
            ordered_names.remove("OpenRouter")
            ordered_names.insert(0, "OpenRouter")
        if target == "openai/gpt-oss-120b" and "Groq" in ordered_names:
            ordered_names.remove("Groq")
            ordered_names.insert(0, "Groq")

        specs: list[ProviderSpec] = []
        for name in [*result.keys()]:
            if name.startswith("User"):
                specs.append(result[name])
        specs.extend(result[name] for name in ordered_names if name not in {p.name for p in specs})
        specs.extend(result[name] for name in result if name not in ordered_names and name not in {p.name for p in specs})
        return specs

    def _openai_headers(self, spec: ProviderSpec, streaming: bool = False) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {spec.key}",
            "User-Agent": "SarembokVE/1.0",
        }
        if streaming:
            headers["Accept"] = "text/event-stream"
        if spec.name.startswith("OpenRouter") or spec.name == "UserOpenRouter":
            headers.update({"HTTP-Referer": "https://sarembok.com", "X-Title": "Sarembok VE"})
        return headers

    def _openai_payload(self, spec: ProviderSpec, messages: list[dict[str, Any]], *, streaming: bool = False, system_prompt: str = "", prompt: str = "", tools: list[dict[str, Any]] | None = None, image_frame: str | None = None) -> dict[str, Any]:
        normalized = list(messages or [])
        if system_prompt and (not normalized or normalized[0].get("role") != "system"):
            normalized.insert(0, {"role": "system", "content": system_prompt})
        if not normalized:
            content: Any = prompt or "Hello"
            if image_frame:
                b64_url = image_frame if image_frame.startswith("data:") else f"data:image/jpeg;base64,{image_frame}"
                content = [{"type": "text", "text": prompt or "Describe this image."}, {"type": "image_url", "image_url": {"url": b64_url, "detail": "low"}}]
            normalized.append({"role": "user", "content": content})
        max_tokens = self.max_output_tokens
        if spec.name.startswith("OpenRouter") or spec.name == "UserOpenRouter":
            max_tokens = min(max_tokens, max(128, int(os.getenv("SAREMBOK_OPENROUTER_MAX_OUTPUT_TOKENS", "1024"))))
        data: dict[str, Any] = {"model": spec.model, "messages": normalized, "max_tokens": max_tokens, "temperature": 0.7}
        if streaming:
            data["stream"] = True
        if tools:
            data["tools"] = tools
            data["tool_choice"] = "auto"
        # Only attach OpenRouter reasoning to OpenRouter requests. Native Groq
        # GPT-OSS reasoning is model-managed and does not need this field.
        if spec.name.startswith("OpenRouter") or spec.name == "UserOpenRouter":
            data["reasoning"] = {"effort": self.openrouter_reasoning, "exclude": True}
        return data

    def _handle_http_error(self, spec: ProviderSpec, exc: urllib.error.HTTPError, attempts: int, deadline: float) -> None:
        body = self._http_error_body(exc)
        classification = self._classify_http_error(body)
        detail = body[:700].replace("\n", " ")

        if exc.code == 429:
            retry = self._retry_after(exc) or self._reset_seconds(exc)
            streak = _PROVIDER_FAILURE_STREAK.get(spec.name, 0) + 1
            _PROVIDER_FAILURE_STREAK[spec.name] = streak
            cooldown = retry or min(60.0, 10.0 * (2 ** min(streak - 1, 2)))
            self._set_provider_cooldown(spec.name, cooldown, state="rate_limited", reason=detail[:240])
            raise RuntimeError(f"{spec.name} rate_limited; provider cooldown={int(cooldown)}s")

        if exc.code in {401, 403}:
            self._set_provider_cooldown(spec.name, 300.0, state="auth_failed", reason=detail[:240])
            raise RuntimeError(f"{spec.name} authentication_failed HTTP {exc.code}")

        if exc.code == 402:
            self._set_provider_cooldown(spec.name, 300.0, state="billing_unavailable", reason=detail[:240])
            raise RuntimeError(f"{spec.name} billing_unavailable HTTP 402")

        if exc.code == 404:
            self._set_provider_cooldown(spec.name, 300.0, state="model_unavailable", reason=detail[:240])
            raise RuntimeError(f"{spec.name} model_unavailable HTTP 404: {detail[:220]}")

        if exc.code not in TRANSIENT_HTTP or attempts >= 2:
            self._set_provider_cooldown(spec.name, 30.0 if exc.code >= 500 else 60.0, state=classification, reason=detail[:240])
            raise RuntimeError(f"{spec.name} HTTP {exc.code}: {detail}")

        delay = min(2.0, 0.35 * (2 ** (attempts - 1)))
        if deadline - time.monotonic() <= delay + 1:
            raise TimeoutError(f"{spec.name} transient HTTP {exc.code}; deadline exceeded")
        time.sleep(delay)

    def _request(self, spec: ProviderSpec, system_prompt: str, prompt: str, messages: list[dict[str, Any]], deadline: float, image_frame: str | None = None) -> tuple[str, dict[str, Any], str]:
        if spec.kind == "gemini":
            clean_b64 = image_frame.split(",", 1)[1] if image_frame and "," in image_frame else image_frame or ""
            parts: list[dict[str, Any]] = [{"text": prompt}]
            if clean_b64:
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": clean_b64}})
            if self.gemini_api == "interactions":
                url = "https://generativelanguage.googleapis.com/v1beta/interactions"
                data = {"model": spec.model, "system_instruction": system_prompt, "input": prompt, "store": False, "generation_config": {"thinking_level": self.gemini_thinking, "max_output_tokens": self.max_output_tokens}}
            else:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{spec.model}:generateContent"
                data = {"system_instruction": {"parts": [{"text": system_prompt}]}, "contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": self.max_output_tokens}}
            headers = {"Content-Type": "application/json", "x-goog-api-key": spec.key}
            api_name = "interactions" if self.gemini_api == "interactions" else "generateContent"
        else:
            url = spec.endpoint
            data = self._openai_payload(spec, messages, system_prompt=system_prompt, prompt=prompt, image_frame=image_frame)
            headers = self._openai_headers(spec)
            api_name = "chat.completions"

        request = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
        attempts = 0
        while True:
            attempts += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("provider deadline exceeded")
            try:
                with urllib.request.urlopen(request, timeout=min(self.provider_timeout, max(1, remaining))) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                text, usage = self._extract_gemini(payload) if spec.kind == "gemini" else self._extract_openai(payload)
                return text, usage, api_name
            except urllib.error.HTTPError as exc:
                self._handle_http_error(spec, exc, attempts, deadline)

    def _request_stream(self, spec: ProviderSpec, system_prompt: str, prompt: str, messages: list[dict[str, Any]], deadline: float, on_delta: Callable[[str], None], image_frame: str | None = None) -> tuple[str, dict[str, Any], str, float]:
        if spec.kind == "gemini":
            clean_b64 = image_frame.split(",", 1)[1] if image_frame and "," in image_frame else image_frame or ""
            parts: list[dict[str, Any]] = [{"text": prompt}]
            if clean_b64:
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": clean_b64}})
            if self.gemini_api == "interactions":
                url = "https://generativelanguage.googleapis.com/v1beta/interactions"
                data = {"model": spec.model, "system_instruction": system_prompt, "input": prompt, "store": False, "stream": True, "generation_config": {"thinking_level": self.gemini_thinking, "max_output_tokens": self.max_output_tokens}}
                api_name = "interactions.stream"
            else:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{spec.model}:streamGenerateContent?alt=sse"
                data = {"system_instruction": {"parts": [{"text": system_prompt}]}, "contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": self.max_output_tokens}}
                api_name = "generateContent.stream"
            headers = {"Content-Type": "application/json", "Accept": "text/event-stream", "x-goog-api-key": spec.key}
        elif spec.kind == "openai":
            url = spec.endpoint
            data = self._openai_payload(spec, messages, streaming=True, system_prompt=system_prompt, prompt=prompt, image_frame=image_frame)
            headers = self._openai_headers(spec, streaming=True)
            api_name = "chat.completions.stream"
        else:
            raise RuntimeError("streaming is unsupported for this provider")

        request = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
        attempts = 0
        while True:
            attempts += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("provider deadline exceeded")
            started = time.monotonic()
            parts_out: list[str] = []
            usage: dict[str, Any] = {}
            ttft_ms: float | None = None
            finish_reason: str | None = None
            try:
                with urllib.request.urlopen(request, timeout=min(self.provider_timeout, max(1, remaining))) as response:
                    for event_name, event in self._sse_events(response):
                        if event is None:
                            continue
                        if not isinstance(event, dict):
                            continue
                        if spec.kind == "gemini":
                            if self.gemini_api == "generatecontent":
                                for candidate in event.get("candidates") or []:
                                    for block in candidate.get("content", {}).get("parts", []) or []:
                                        if isinstance(block, dict) and block.get("text"):
                                            chunk = str(block["text"])
                                            if ttft_ms is None:
                                                ttft_ms = round((time.monotonic() - started) * 1000, 1)
                                            parts_out.append(chunk)
                                            on_delta(chunk)
                                usage = event.get("usageMetadata") or usage
                            else:
                                delta = event.get("delta") or {}
                                if delta.get("type") == "text" and delta.get("text"):
                                    chunk = str(delta["text"])
                                    if ttft_ms is None:
                                        ttft_ms = round((time.monotonic() - started) * 1000, 1)
                                    parts_out.append(chunk)
                                    on_delta(chunk)
                                usage = event.get("usage") or usage
                        else:
                            choices = event.get("choices") or []
                            if choices:
                                choice = choices[0] or {}
                                finish_reason = choice.get("finish_reason") or finish_reason
                                delta = choice.get("delta") or {}
                                content = delta.get("content")
                                if isinstance(content, list):
                                    content = "".join(str(x.get("text", "")) for x in content if isinstance(x, dict) and x.get("type") == "text")
                                if content:
                                    chunk = str(content)
                                    if ttft_ms is None:
                                        ttft_ms = round((time.monotonic() - started) * 1000, 1)
                                    parts_out.append(chunk)
                                    on_delta(chunk)
                            usage = event.get("usage") or usage
                if not parts_out:
                    raise ProviderStreamError(f"{spec.name} stream returned no assistant content; finish_reason={finish_reason}")
                if finish_reason:
                    usage = dict(usage)
                    usage["_finish_reason"] = finish_reason
                return "".join(parts_out).strip(), usage, api_name, ttft_ms or round((time.monotonic() - started) * 1000, 1)
            except urllib.error.HTTPError as exc:
                if parts_out:
                    raise ProviderStreamError(f"{spec.name} stream failed after partial output", partial=True) from exc
                self._handle_http_error(spec, exc, attempts, deadline)
            except ProviderStreamError:
                raise
            except Exception as exc:
                if parts_out:
                    raise ProviderStreamError(f"{spec.name} stream failed after partial output: {exc}", partial=True) from exc
                raise

    def _attempt(self, spec: ProviderSpec, system_prompt: str, prompt: str, messages: list[dict[str, Any]], deadline: float, on_delta: Callable[[str], None] | None, image_frame: str | None) -> ProviderResult:
        started = time.monotonic()
        if on_delta is None:
            text, usage, api = self._request(spec, system_prompt, prompt, messages, deadline, image_frame=image_frame)
            ttft = None
        else:
            text, usage, api, ttft = self._request_stream(spec, system_prompt, prompt, messages, deadline, on_delta, image_frame=image_frame)
        latency = round((time.monotonic() - started) * 1000, 1)
        return ProviderResult(text, spec.name, spec.model, latency, 1, api, usage, ttft)

    def _generate(self, system_prompt: str, prompt: str, messages: list[dict[str, Any]], *, on_delta: Callable[[str], None] | None, requested_model: str | None, image_frame: str | None, dynamic_key: str | None) -> ProviderResult:
        providers = self.configured(requested_model=requested_model, dynamic_key=dynamic_key)
        if not providers:
            raise RuntimeError("no language-model provider configured")
        deadline = time.monotonic() + self.total_timeout
        failures: list[str] = []
        for spec in providers:
            if not self._provider_available(spec.name):
                logger.info("provider_skipped provider=%s model=%s reason=cooldown", spec.name, spec.model)
                failures.append(f"{spec.name}:cooldown")
                continue
            started = time.monotonic()
            try:
                result = self._attempt(spec, system_prompt, prompt, messages, deadline, on_delta, image_frame)
                self._mark_success(spec.name)
                record = {
                    "provider": spec.name,
                    "model": spec.model,
                    "latency_ms": result.latency_ms,
                    "ttft_ms": result.ttft_ms,
                    "attempts": result.attempts,
                    "api": result.api,
                    "ok": True,
                    "timestamp": time.time(),
                }
                self._history.append(record)
                logger.info("provider_success provider=%s model=%s latency_ms=%s ttft_ms=%s api=%s finish_reason=%s", spec.name, spec.model, result.latency_ms, result.ttft_ms, result.api, result.usage.get("_finish_reason"))
                return result
            except ProviderStreamError as exc:
                failures.append(f"{spec.name}:RuntimeError")
                latency = round((time.monotonic() - started) * 1000, 1)
                self._history.append({"provider": spec.name, "model": spec.model, "latency_ms": latency, "attempts": 1, "api": "chat.completions.stream", "ok": False, "error": type(exc).__name__, "error_message": str(exc), "partial": exc.partial, "timestamp": time.time()})
                logger.warning("provider_failed provider=%s model=%s error_type=%s error=%s", spec.name, spec.model, type(exc).__name__, exc)
                if exc.partial:
                    raise RuntimeError(str(exc)) from exc
            except Exception as exc:
                latency = round((time.monotonic() - started) * 1000, 1)
                failures.append(f"{spec.name}:{type(exc).__name__}")
                self._history.append({"provider": spec.name, "model": spec.model, "latency_ms": latency, "attempts": 1, "api": "chat.completions", "ok": False, "error": type(exc).__name__, "error_message": str(exc), "timestamp": time.time()})
                logger.warning("provider_failed provider=%s model=%s error_type=%s error=%s", spec.name, spec.model, type(exc).__name__, str(exc))
        raise RuntimeError("all providers failed: " + ",".join(failures))

    def generate_stream(self, system_prompt: str, prompt: str, messages: list[dict[str, Any]], on_delta: Callable[[str], None], requested_model: str | None = None, image_frame: str | None = None, dynamic_key: str | None = None) -> ProviderResult:
        return self._generate(system_prompt, prompt, messages, on_delta=on_delta, requested_model=requested_model, image_frame=image_frame, dynamic_key=dynamic_key)

    def generate(self, system_prompt: str, prompt: str, messages: list[dict[str, Any]], requested_model: str | None = None, image_frame: str | None = None, dynamic_key: str | None = None) -> ProviderResult:
        callback = _STREAM_CALLBACK.get()
        return self._generate(system_prompt, prompt, messages, on_delta=callback, requested_model=requested_model, image_frame=image_frame, dynamic_key=dynamic_key)

    def metrics(self) -> dict[str, Any]:
        now = time.monotonic()
        cooldowns = {name: max(0, round(until - now, 1)) for name, until in _PROVIDER_COOLDOWNS.items() if until > now}
        configured = []
        for spec in self.configured():
            status = dict(_PROVIDER_STATUS.get(spec.name) or {})
            configured.append({"name": spec.name, "model": spec.model, "api": "generateContent" if spec.kind == "gemini" else "chat.completions", "health": status.get("state", "unknown"), "cooldownSeconds": status.get("cooldownSeconds", cooldowns.get(spec.name, 0)), "reason": status.get("reason", "")})
        entries = list(self._history)
        successes = [entry for entry in entries if entry.get("ok")]
        return {
            "configuredProviders": configured,
            "samples": len(entries),
            "successes": len(successes),
            "failures": len(entries) - len(successes),
            "cooldowns": cooldowns,
            "health": {name: dict(value) for name, value in _PROVIDER_STATUS.items()},
            "recent": entries[-20:],
        }
