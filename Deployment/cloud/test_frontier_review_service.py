import os
import unittest
from unittest.mock import patch

from frontier_review_service import run_frontier_review


class FrontierReviewServiceTests(unittest.TestCase):
    def test_no_credentials_means_no_external_calls(self):
        with patch.dict(os.environ, {}, clear=True):
            result = run_frontier_review(
                task="test",
                implementation_summary="summary",
                verification="verified",
            )
        self.assertFalse(result["enabled"])
        self.assertEqual(0, result["reviewCount"])

    def test_openai_and_anthropic_are_independent(self):
        openai_response = {
            "output_text": "OPENAI_REVIEW_OK",
            "output": [],
        }
        anthropic_response = {
            "content": [{"type": "text", "text": "ANTHROPIC_REVIEW_OK"}],
        }
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-openai", "ANTHROPIC_API_KEY": "test-anthropic"},
            clear=True,
        ), patch("frontier_review_service._request_json", side_effect=[openai_response, anthropic_response]) as request:
            result = run_frontier_review(
                task="provider routing",
                implementation_summary="open model first",
                verification="tests pass",
            )
        self.assertTrue(result["enabled"])
        self.assertEqual(2, result["reviewCount"])
        self.assertEqual(2, request.call_count)
        self.assertTrue(all(item["ok"] for item in result["reviews"]))
        self.assertEqual("OPENAI_REVIEW_OK", result["reviews"][0]["findings"])
        self.assertEqual("ANTHROPIC_REVIEW_OK", result["reviews"][1]["findings"])


if __name__ == "__main__":
    unittest.main()
