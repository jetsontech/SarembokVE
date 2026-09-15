"""SarembokVE frontier engineering review council.

The council is an optional review layer. It never becomes a hard dependency for
normal Sarembok operation: open-weight execution remains the preferred path.
External frontier models are used for independent critique, not ownership of the
runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any


@dataclass(frozen=True)
class ReviewModel:
    name: str
    provider: str
    model_id: str
    role: str
    external: bool = True


# Current model targets. Availability is intentionally key-gated at runtime;
# this registry must never imply that a secret or paid service is configured.
REVIEW_MODELS: tuple[ReviewModel, ...] = (
    ReviewModel(
        "OpenAI Codex Max",
        "OpenAI",
        "gpt-5.1-codex-max",
        "long-horizon coding, architecture, and implementation review",
    ),
    ReviewModel(
        "Claude Opus",
        "Anthropic",
        "claude-opus-4-8",
        "independent architecture, reasoning, and adversarial review",
    ),
)


def configured_review_models() -> list[ReviewModel]:
    """Return only review models whose provider credential is configured."""
    result: list[ReviewModel] = []
    if os.getenv("OPENAI_API_KEY", "").strip():
        result.append(REVIEW_MODELS[0])
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        result.append(REVIEW_MODELS[1])
    return result


def review_policy() -> dict[str, Any]:
    configured = configured_review_models()
    return {
        "enabled": bool(configured),
        "mode": "independent-review-only",
        "executionPreference": "open-weight-first",
        "humanDecisionGate": True,
        "models": [
            {
                "name": model.name,
                "provider": model.provider,
                "model": model.model_id,
                "role": model.role,
                "configured": model in configured,
            }
            for model in REVIEW_MODELS
        ],
        "configuredCount": len(configured),
    }


def build_review_prompt(*, task: str, implementation_summary: str, verification: str) -> str:
    """Build a compact, model-neutral review packet.

    The packet is intentionally bounded: the council reviews the decision and
    proof rather than receiving the entire repository indiscriminately.
    """
    return (
        "You are an independent engineering reviewer for SarembokVE.\n"
        "Review the supplied implementation for correctness, maintainability, "
        "security, regression risk, and deterministic verification. Do not "
        "rewrite working architecture without evidence. Return concrete findings.\n\n"
        f"TASK:\n{task.strip()}\n\n"
        f"IMPLEMENTATION SUMMARY:\n{implementation_summary.strip()}\n\n"
        f"VERIFICATION:\n{verification.strip()}\n"
    )
