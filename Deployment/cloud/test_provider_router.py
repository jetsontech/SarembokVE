from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import provider_router as pr


class FakeHTTPError:
    def __init__(self, code: int, body: bytes = b"", headers: dict[str, str] | None = None) -> None:
        self.code = code
        self._body = body
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body


class ProviderRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        pr._PROVIDER_COOLDOWNS.clear()
        pr._PROVIDER_STATUS.clear()
        pr._PROVIDER_FAILURE_STREAK.clear()

    def test_gemini_alias_is_current_openrouter_latest_alias(self) -> None:
        router = pr.ProviderRouter()
        self.assertEqual(router.resolve_model_id("gemini-flash"), "~google/gemini-flash-latest")

    def test_explicit_openrouter_model_precedes_groq_but_groq_keeps_native_model(self) -> None:
        env = {
            "OPENROUTER_API_KEY": "or-test",
            "GROQ_API_KEY": "gsk-test",
            "SAREMBOK_PROVIDER_ORDER": "Groq,OpenRouter",
            "OPENROUTER_MODEL": "openai/gpt-4o-mini",
            "GROQ_MODEL": "openai/gpt-oss-120b",
        }
        with patch.dict(os.environ, env, clear=False):
            specs = pr.ProviderRouter().configured(requested_model="gemini-flash")
        self.assertEqual([spec.name for spec in specs[:2]], ["OpenRouter", "Groq"])
        self.assertEqual(specs[0].model, "~google/gemini-flash-latest")
        self.assertEqual(specs[1].model, "openai/gpt-oss-120b")

    def test_402_enters_billing_cooldown(self) -> None:
        router = pr.ProviderRouter()
        spec = pr.ProviderSpec("OpenRouter", "openai/gpt-4o-mini", "openai", "https://example.invalid", "test")
        response = FakeHTTPError(402, b'{"error":{"message":"This request requires more credits","code":402}}')
        with self.assertRaisesRegex(RuntimeError, "billing_unavailable"):
            router._handle_http_error(spec, response, 1, 9999999999)
        self.assertFalse(router._provider_available("OpenRouter"))
        self.assertEqual(pr._PROVIDER_STATUS["OpenRouter"]["state"], "billing_unavailable")

    def test_429_uses_retry_after(self) -> None:
        router = pr.ProviderRouter()
        spec = pr.ProviderSpec("Groq", "openai/gpt-oss-120b", "openai", "https://example.invalid", "test")
        response = FakeHTTPError(429, b'{"error":{"message":"rate limit"}}', {"Retry-After": "17"})
        with self.assertRaisesRegex(RuntimeError, "cooldown=17s"):
            router._handle_http_error(spec, response, 1, 9999999999)
        self.assertFalse(router._provider_available("Groq"))

    def test_no_duplicate_openrouter_fallback_spec(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-test", "SAREMBOK_PROVIDER_ORDER": "Groq,OpenRouter"}, clear=False):
            specs = pr.ProviderRouter().configured(requested_model="openai/gpt-oss-120b")
        self.assertEqual(sum(1 for spec in specs if spec.name == "OpenRouter"), 1)
        self.assertEqual(sum(1 for spec in specs if spec.name == "Groq"), 1)


if __name__ == "__main__":
    unittest.main()
