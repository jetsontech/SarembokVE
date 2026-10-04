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
            self.assertIn("sarembokve", res["model"])
            self.assertEqual(res["provider"], "SarembokVE Visual Synthesis Engine")
            self.assertEqual(res["badge"], "⚡ SAREMBOKVE VISUAL SYNTHESIS")

    def test_visual_engine_status(self):
        status = get_visual_engine_status()
        self.assertIn("activeTier", status)
        self.assertIn("SarembokVE", status["activeTier"])
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
            self.assertIn("url", res)
            self.assertIn("Tier 2", res["tier"])

    def test_zk_gloss_mockup_resolution(self):
        res_tube = resolve_image_generation("generate a design mockup for Z & K Gloss lip gloss brand with Shine Bright")
        self.assertEqual(res_tube["url"], "/api/download?fileId=zk_gloss_mockup")
        self.assertEqual(res_tube["provider"], "SarembokVE Visual Synthesis Engine")
        self.assertEqual(res_tube["badge"], "⚡ SAREMBOKVE VISUAL SYNTHESIS")

        res_retail = resolve_image_generation("generate point of sale retail counter display for Z & K Gloss lip gloss brand in stores")
        self.assertEqual(res_retail["url"], "/api/download?fileId=zk_retail_display")
        self.assertEqual(res_retail["provider"], "SarembokVE Visual Synthesis Engine")


if __name__ == "__main__":
    unittest.main()
