import os
import unittest
from unittest.mock import patch

from open_model_registry import get_open_model, get_open_models, capability_inventory
from frontier_review_council import configured_review_models, review_policy, build_review_prompt


class OpenModelRegistryTests(unittest.TestCase):
    def test_open_models_are_capability_driven(self):
        models = get_open_models("coding")
        self.assertTrue(models)
        self.assertTrue(all(model.supports("coding") for model in models))
        self.assertIsNotNone(get_open_model("openai/gpt-oss-120b"))

    def test_inventory_does_not_require_provider_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            inventory = capability_inventory()
        self.assertEqual("WE DON'T BUY IT. WE BUILD IT.", inventory["principle"])
        self.assertGreaterEqual(inventory["openModelCount"], 5)
        self.assertEqual([], inventory["localOpenModels"])


class FrontierReviewCouncilTests(unittest.TestCase):
    def test_review_is_disabled_without_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual([], configured_review_models())
            self.assertFalse(review_policy()["enabled"])

    def test_each_configured_provider_is_optional(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True):
            models = configured_review_models()
        self.assertEqual(["OpenAI Codex Max"], [model.name for model in models])

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}, clear=True):
            models = configured_review_models()
        self.assertEqual(["Claude Opus"], [model.name for model in models])

    def test_review_prompt_is_bounded_and_model_neutral(self):
        prompt = build_review_prompt(
            task="Fix provider fallback",
            implementation_summary="Added cooldown classification",
            verification="Provider tests pass",
        )
        self.assertIn("Fix provider fallback", prompt)
        self.assertIn("Provider tests pass", prompt)
        self.assertNotIn("OPENAI_API_KEY", prompt)
        self.assertNotIn("ANTHROPIC_API_KEY", prompt)


if __name__ == "__main__":
    unittest.main()
