import os
import unittest
from unittest.mock import patch

# Production installs the fabric through sitecustomize. Tests must install the
# same runtime bridge explicitly because Python may load sitecustomize before
# the test directory is added to sys.path.
import sitecustomize  # noqa: F401
from open_model_fabric import install as install_open_model_fabric
from provider_router import ProviderRouter

# Make the test contract deterministic regardless of Python startup ordering.
install_open_model_fabric()


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

    def test_dynamic_user_key_keeps_provider_native_default(self):
        router = ProviderRouter()
        with patch.dict(
            os.environ,
            {
                "LLM_MODEL": "gpt-5.6-luna",
            },
            clear=True,
        ):
            specs = router.configured(dynamic_key="sk-test")
        self.assertEqual("UserOpenAI", specs[0].name)
        self.assertEqual("gpt-5.6-luna", specs[0].model)

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
