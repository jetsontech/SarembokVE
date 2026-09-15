import os
import unittest
from unittest.mock import patch

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

    def test_explicit_model_still_wins(self):
        router = ProviderRouter()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}, clear=True):
            specs = router.configured(requested_model="llama-3.3-70b")
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
