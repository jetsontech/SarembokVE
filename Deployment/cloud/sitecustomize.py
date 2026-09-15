"""SarembokVE process bootstrap safeguards.

The runtime must never silently fall back to a tiny completion budget,
and browser speech must never receive decorative emoji characters.
"""
from __future__ import annotations

import os
import re

os.environ.setdefault("SAREMBOK_LLM_MAX_OUTPUT_TOKENS", "8192")

_EMOJI_RE = re.compile(r"[\U0001F1E0-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")

_PRODUCT_DIRECTIVE = (
    "SAREMBOKVE PRODUCT IDENTITY: Sarembok V E is an AI-native computing environment "
    "and sovereign control plane, not merely a chatbot or thin model wrapper. "
    "It provides a runtime for agent lifecycle, persistent memory, tool execution, "
    "research, orchestration, provider abstraction, worker/compute scheduling, and "
    "multimodal interaction where enabled. When explaining Sarembok V E, describe the "
    "computing environment and runtime architecture first; conversation is one interface. "
    "Do not reduce Sarembok V E to a chat application. Do not claim capabilities that "
    "are not supported by the authoritative runtime context. Produce complete answers "
    "that finish the requested task. Do not use emoji or decorative Unicode symbols "
    "in assistant responses."
)


def _strip_emoji(value: str) -> str:
    text = str(value or "")
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def _system_prompt(system_prompt: str) -> str:
    base = str(system_prompt or "").strip()
    return f"{_PRODUCT_DIRECTIVE}\n\n{base}" if base else _PRODUCT_DIRECTIVE


try:
    from provider_router import ProviderRouter

    _original_init = ProviderRouter.__init__

    def _init_with_full_budget(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        try:
            self.max_output_tokens = max(8192, int(os.getenv("SAREMBOK_LLM_MAX_OUTPUT_TOKENS", "8192")))
        except ValueError:
            self.max_output_tokens = 8192

    ProviderRouter.__init__ = _init_with_full_budget

    _original_openai_payload = ProviderRouter._openai_payload

    def _openai_payload_with_full_budget(self, spec, messages, streaming=False, system_prompt="", prompt="", tools=None, image_frame=None):
        data = _original_openai_payload(
            self,
            spec,
            messages,
            streaming=streaming,
            system_prompt=_system_prompt(system_prompt),
            prompt=prompt,
            tools=tools,
            image_frame=image_frame,
        )
        try:
            budget = max(8192, int(os.getenv("SAREMBOK_LLM_MAX_OUTPUT_TOKENS", "8192")))
        except ValueError:
            budget = 8192
        data["max_tokens"] = budget
        return data

    ProviderRouter._openai_payload = _openai_payload_with_full_budget

    _original_generate_stream = ProviderRouter.generate_stream

    def _generate_stream_without_emoji(self, system_prompt, prompt, messages, on_delta, requested_model=None, image_frame=None, dynamic_key=None):
        def safe_delta(delta):
            cleaned = _strip_emoji(delta)
            if cleaned:
                on_delta(cleaned)

        result = _original_generate_stream(
            self,
            _system_prompt(system_prompt),
            prompt,
            messages,
            safe_delta,
            requested_model=requested_model,
            image_frame=image_frame,
            dynamic_key=dynamic_key,
        )
        result.text = _strip_emoji(result.text)
        return result

    ProviderRouter.generate_stream = _generate_stream_without_emoji

    _original_generate = ProviderRouter.generate

    def _generate_without_emoji(self, system_prompt, prompt, messages, requested_model=None, image_frame=None, dynamic_key=None):
        result = _original_generate(
            self,
            _system_prompt(system_prompt),
            prompt,
            messages,
            requested_model=requested_model,
            image_frame=image_frame,
            dynamic_key=dynamic_key,
        )
        result.text = _strip_emoji(result.text)
        return result

    ProviderRouter.generate = _generate_without_emoji
except Exception:
    # Never prevent the runtime from starting because of a safeguard.
    pass


# Frontier open-model fabric: make the capability registry an actual routing
# input before the runtime creates its ProviderRouter singleton. This remains
# fail-safe and preserves the original provider behavior if the registry is
# unavailable.
try:
    from open_model_fabric import install as _install_open_model_fabric
    _install_open_model_fabric()
except Exception:
    pass


# Browser-session least privilege boundary.
# knowledge_rpc_server loads server.py through importlib under the stable module
# name "sarembok_cloud_server". Wrap that loader so the session scope is reduced
# before knowledge_rpc_server captures the runtime dispatch function.
#
# These methods cover the public browser product surface: chat, runtime
# telemetry, user-owned memory/session data, feedback, media/vision features,
# digital-human lifecycle, and read-only worker/task/MCP visibility. Administrative
# execution, worker registration/control, GPU rental, master/social authentication,
# arbitrary compute execution, task mutation, and MCP registration are deliberately
# excluded from the browser bearer session.
try:
    import importlib.util as _importlib_util

    _original_spec_from_file_location = _importlib_util.spec_from_file_location

    _BROWSER_SESSION_LEAST_PRIVILEGE_METHODS = {
        "SarembokChat",
        "GetRuntimeInfo",
        "GetProviderMetrics",
        "BrowserNavigate",
        "BrowserScreenshot",
        "BrowserRender",
        "CreateDigitalHumanSession",
        "GetDigitalHumanSession",
        "ListDigitalHumanSessions",
        "CloseDigitalHumanSession",
        "SubmitFeedback",
        "GetFeedbackSummary",
        "SearchMemories",
        "StoreMemory",
        "ListMemories",
        "ListWorkers",
        "ListTasks",
        "GenerateImage",
        "GetVisualEngineStatus",
        "GetVisionStatus",
        "SearchYouTube",
        "ResolveMediaStream",
        "ListMcpServers",
        "CancelActiveStream",
        "SpatialVisualRecall",
        "GetCurrentUser",
        "ListUserChatSessions",
        "SaveUserChatSession",
    }

    class _CloudServerLoaderProxy:
        def __init__(self, loader):
            self._loader = loader

        def create_module(self, spec):
            create = getattr(self._loader, "create_module", None)
            return create(spec) if create else None

        def exec_module(self, module):
            self._loader.exec_module(module)
            allowed = set(_BROWSER_SESSION_LEAST_PRIVILEGE_METHODS)
            module.BROWSER_ALLOWED_METHODS = allowed
            log = getattr(module, "LOG", None)
            if log is not None:
                log.info("browser_session_policy applied methods=%d", len(allowed))

        def __getattr__(self, name):
            return getattr(self._loader, name)

    def _secure_spec_from_file_location(name, location, *args, **kwargs):
        spec = _original_spec_from_file_location(name, location, *args, **kwargs)
        if spec is not None and name == "sarembok_cloud_server" and str(location) == "/app/server.py" and spec.loader is not None:
            spec.loader = _CloudServerLoaderProxy(spec.loader)
        return spec

    _importlib_util.spec_from_file_location = _secure_spec_from_file_location
except Exception:
    # Never prevent the runtime from starting because of a safeguard.
    pass
