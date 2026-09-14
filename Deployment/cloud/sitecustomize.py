"""SarembokVE process bootstrap safeguards.

The runtime must never silently fall back to a tiny completion budget.
This module is loaded by Python's site initialization before server imports.
"""
from __future__ import annotations

import os

# Preserve explicit deployment values, but establish a safe frontier default.
os.environ.setdefault("SAREMBOK_LLM_MAX_OUTPUT_TOKENS", "8192")

try:
    from provider_router import ProviderRouter

    _original_openai_payload = ProviderRouter._openai_payload

    def _openai_payload_with_full_budget(self, spec, messages, streaming=False, system_prompt="", prompt="", tools=None, image_frame=None):
        data = _original_openai_payload(
            self,
            spec,
            messages,
            streaming=streaming,
            system_prompt=system_prompt,
            prompt=prompt,
            tools=tools,
            image_frame=image_frame,
        )
        # The previous provider-router revision silently capped OpenRouter at
        # 200 tokens. That truncates ordinary technical answers mid-sentence.
        # All configured providers receive the authoritative runtime budget.
        try:
            budget = max(64, int(os.getenv("SAREMBOK_LLM_MAX_OUTPUT_TOKENS", "8192")))
        except ValueError:
            budget = 8192
        data["max_tokens"] = budget
        return data

    ProviderRouter._openai_payload = _openai_payload_with_full_budget
except Exception:
    # Never prevent the runtime from starting because of the safeguard.
    pass
