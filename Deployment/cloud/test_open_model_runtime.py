import os
import unittest
from unittest.mock import patch

# Production starts this hook automatically; importing it explicitly makes the
# contract test independent of the test runner's sys.path startup behavior.
import sitecustomize  # noqa: F401
from provider_router import ProviderRouter


class OpenModelRuntimeTests(unittest.TestCase):
    def test_default_runtime_selection_is_open_model(self):
        router = ProviderRouter()
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "gsk_test",
                "SAREMBOK_PROVIDER_ORDER": "Groq,OpenRouter,Gemini,OpenAI,Custom",
                "SAREMBOK_OPEN_MODEL": "openai/gpt-oss-120b",
            },
            clear=True,
        ):
            specs = router.configured()
        self.assertTrue(specs)
        self.assertEqual("Groq", specs[0].name)
        self.assertEqual("openai/gpt-oss-120b", specs[0].model)

    def test_invalid_default_model_falls_back_to_registered_open_model(self):
        router = ProviderRouter()
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "gsk_test",
                "SAREMBOK_OPEN_MODEL": "not-a-real-registered-model",
                "SAREMBOK_PROVIDER_ORDER": "Groq",
            },
            clear=True,
        ):
            specs = router.configured()
        self.assertEqual("Groq", specs[0].name)
        self.assertEqual("openai/gpt-oss-120b", specs[0].model)

    def test_explicit_open_model_routes_to_requested_openrouter_model(self):
        router = ProviderRouter()
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "sk-or-test",
                "SAREMBOK_PROVIDER_ORDER": "OpenRouter",
            },
            clear=True,
        ):
            specs = router.configured(requested_model="llama-3.3-70b")
        self.assertEqual("OpenRouter", specs[0].name)
        self.assertEqual("meta-llama/llama-3.3-70b-instruct", specs[0].model)

    def test_metrics_expose_open_model_fabric(self):
        router = ProviderRouter()
        with patch.dict(os.environ, {"SAREMBOK_OPEN_MODEL": "openai/gpt-oss-120b"}, clear=True):
            metrics = router.metrics()
        self.assertIn("openModelFabric", metrics)
        self.assertTrue(metrics["openModelFabric"]["enabled"])
        self.assertTrue(metrics["openModelFabric"]["defaultModelRegistered"])


if __name__ == "__main__":
    unittest.main()
