"""Unit tests for the 3-tier adaptive visual synthesis router."""
import os
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

cloud_dir = str(Path(__file__).resolve().parent)
if cloud_dir not in sys.path:
    sys.path.insert(0, cloud_dir)

from server import resolve_image_generation, get_visual_engine_status


class TestVisualRouter(unittest.TestCase):
    def test_tier3_default_fallback(self):
        with patch.dict(os.environ, {"FAL_KEY": "", "TOGETHER_API_KEY": "", "OPENAI_API_KEY": ""}, clear=False):
            res = resolve_image_generation("cybernetic matrix core", aspect_ratio="1:1")
            self.assertIn("url", res)
            self.assertIn("pollinations.ai", res["url"])
            self.assertEqual(res["tier"], "Tier 3 (Zero-Key Community Fallback)")
            self.assertEqual(res["model"], "flux.1-schnell")

    def test_visual_engine_status(self):
        status = get_visual_engine_status()
        self.assertIn("activeTier", status)
        self.assertIn("tier1_sovereign", status)
        self.assertIn("tier2_enterprise", status)
        self.assertIn("tier3_community", status)

    @patch("urllib.request.urlopen")
    def test_tier2_fal_routing(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"images": [{"url": "https://fal.media/files/flux_test.png"}]}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with patch.dict(os.environ, {"FAL_KEY": "fake-fal-key"}, clear=False):
            res = resolve_image_generation("hyper-dense neon tokyo", preferred_engine="fal")
            self.assertEqual(res["provider"], "Fal.ai Enterprise")
            self.assertEqual(res["url"], "https://fal.media/files/flux_test.png")
            self.assertIn("Tier 2", res["tier"])


if __name__ == "__main__":
    unittest.main()
