"""Regression tests for fail-closed local-only model routing.

Run from the repository root:
    python -m unittest Deployment.cloud.test_local_only_routing -v

These tests verify application-level routing. They do not replace a production
network-egress test or prove that an inference endpoint is reachable.
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from Deployment.cloud.provider_router import ProviderRouter


class LocalOnlyRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(
            os.environ,
            {
                "SAREMBOK_LOCAL_ONLY": "true",
                "SAREMBOK_LOCAL_GEMMA_URL": "http://sarembok-local-gemma:8080/v1/chat/completions",
                "SAREMBOK_LOCAL_GEMMA_MODEL": "gemma-local-test",
                "SAREMBOK_LOCAL_GEMMA_KEY": "test-local-key",
                "OPENAI_API_KEY": "test-openai-key",
                "OPENROUTER_API_KEY": "test-openrouter-key",
                "GROQ_API_KEY": "test-groq-key",
                "GEMINI_API_KEY": "test-gemini-key",
                "LLM_ENDPOINT_URL": "https://example.invalid/v1/chat/completions",
                "SAREMBOK_PROVIDER_ORDER": "Gemini,OpenRouter,Groq,OpenAI,Custom",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_local_only_ignores_external_keys_and_requested_model(self) -> None:
        router = ProviderRouter()
        providers = router.configured(
            requested_model="gemini-3.8-flash",
            dynamic_key="AIza-test-dynamic-key",
        )
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].name, "LocalGemma")
        self.assertEqual(providers[0].model, "gemma-local-test")
        self.assertEqual(
            providers[0].endpoint,
            "http://sarembok-local-gemma:8080/v1/chat/completions",
        )

    def test_generate_calls_only_local_provider(self) -> None:
        router = ProviderRouter()
        with patch.object(
            router, "_request", return_value=("local response", {}, "chat.completions")
        ) as request:
            result = router.generate(
                "system",
                "test prompt",
                [],
                requested_model="gemini-3.8-flash",
                dynamic_key="AIza-test-dynamic-key",
            )
        self.assertEqual(result.provider, "LocalGemma")
        self.assertEqual(result.model, "gemma-local-test")
        self.assertEqual(request.call_args.args[0].name, "LocalGemma")
        request.assert_called_once()

    def test_missing_local_endpoint_fails_closed(self) -> None:
        os.environ.pop("SAREMBOK_LOCAL_GEMMA_URL", None)
        router = ProviderRouter()
        self.assertEqual(router.configured(), [])
        with self.assertRaisesRegex(RuntimeError, "local_only_configuration_error"):
            router.generate("system", "test prompt", [])

    def test_missing_local_model_name_fails_closed(self) -> None:
        os.environ.pop("SAREMBOK_LOCAL_GEMMA_MODEL", None)
        router = ProviderRouter()
        self.assertEqual(router.configured(), [])
        with self.assertRaisesRegex(RuntimeError, "local_only_configuration_error"):
            router.generate("system", "test prompt", [])


if __name__ == "__main__":
    unittest.main()
