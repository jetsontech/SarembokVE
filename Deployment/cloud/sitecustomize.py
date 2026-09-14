"""SarembokVE process bootstrap safeguards.

The runtime must never silently fall back to a tiny completion budget,
and browser speech must never receive decorative emoji characters.
"""
from __future__ import annotations

import os
import re

os.environ.setdefault("SAREMBOK_LLM_MAX_OUTPUT_TOKENS", "8192")

_EMOJI_RE = re.compile(r"[\U0001F1E0-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")


def _strip_emoji(value: str) -> str:
    text = str(value or "")
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


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
            system_prompt=system_prompt,
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
            system_prompt,
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
            system_prompt,
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
