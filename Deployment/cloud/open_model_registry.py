"""SarembokVE open-weight model capability registry.

The registry is deliberately provider-neutral. A model can be reached through a
hosted inference service today and a Sarembok-owned GPU worker tomorrow without
changing the capability contract used by routing and agents.

Principle: WE DON'T BUY IT. WE BUILD IT.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Any


@dataclass(frozen=True)
class OpenModelSpec:
    model_id: str
    family: str
    capabilities: frozenset[str]
    tool_calling: bool
    context_window: int
    local_inference: bool = True
    default_priority: int = 100
    license: str = "unknown"
    gpu_class: str = "unknown"
    inference_backends: tuple[str, ...] = ()

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["capabilities"] = sorted(self.capabilities)
        value["inference_backends"] = list(self.inference_backends)
        return value


# IDs are stable capability identifiers, not a claim that every model is
# installed locally. Availability is determined by the provider/worker layer.
OPEN_MODELS: tuple[OpenModelSpec, ...] = (
    OpenModelSpec(
        "openai/gpt-oss-120b", "GPT-OSS", frozenset({"general", "reasoning", "coding", "agentic"}),
        True, 131072, default_priority=10, license="Apache-2.0", gpu_class="80GB+", inference_backends=("groq", "vllm", "transformers"),
    ),
    OpenModelSpec(
        "deepseek/deepseek-v3", "DeepSeek", frozenset({"general", "reasoning", "coding", "agentic"}),
        True, 128000, default_priority=20, license="MIT", gpu_class="80GB+", inference_backends=("vllm", "sglang", "openrouter"),
    ),
    OpenModelSpec(
        "qwen/qwen3-coder", "Qwen", frozenset({"coding", "reasoning", "agentic", "general"}),
        True, 262144, default_priority=25, license="Apache-2.0", gpu_class="48GB+", inference_backends=("vllm", "sglang", "openrouter"),
    ),
    OpenModelSpec(
        "meta-llama/llama-3.3-70b-instruct", "Llama", frozenset({"general", "coding", "agentic"}),
        True, 131072, default_priority=30, license="Llama", gpu_class="48GB+", inference_backends=("vllm", "transformers", "groq"),
    ),
    OpenModelSpec(
        "mistralai/mistral-large", "Mistral", frozenset({"general", "coding", "agentic"}),
        True, 128000, default_priority=35, license="Apache-2.0", gpu_class="48GB+", inference_backends=("vllm", "mistral", "openrouter"),
    ),
    OpenModelSpec(
        "z-ai/glm-4.5", "GLM", frozenset({"general", "reasoning", "coding", "agentic"}),
        True, 131072, default_priority=40, license="Apache-2.0", gpu_class="48GB+", inference_backends=("vllm", "sglang", "openrouter"),
    ),
)


def get_open_models(capability: str | None = None) -> list[OpenModelSpec]:
    models = [m for m in OPEN_MODELS if not capability or m.supports(capability)]
    return sorted(models, key=lambda m: m.default_priority)


def get_open_model(model_id: str) -> OpenModelSpec | None:
    needle = model_id.strip().lower()
    return next((m for m in OPEN_MODELS if m.model_id.lower() == needle), None)


def local_model_ids() -> set[str]:
    """Return models explicitly declared as locally available by the worker fabric."""
    raw = os.getenv("SAREMBOK_LOCAL_OPEN_MODELS", "").strip()
    return {item.strip() for item in raw.split(",") if item.strip()}


def capability_inventory() -> dict[str, Any]:
    local = local_model_ids()
    return {
        "principle": "WE DON'T BUY IT. WE BUILD IT.",
        "openModelCount": len(OPEN_MODELS),
        "localOpenModels": sorted(local),
        "models": [m.to_dict() for m in OPEN_MODELS],
    }
