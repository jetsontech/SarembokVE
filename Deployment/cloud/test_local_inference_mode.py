"""Test suite for SarembokVE Local-Only Mode and Local Inference Router."""
import os
import unittest
from unittest.mock import patch, MagicMock

from provider_router import ProviderRouter, ProviderSpec, _LOCAL_INFERENCE_SEMAPHORE


class TestLocalInferenceMode(unittest.TestCase):
    def setUp(self):
        # Reset environment before each test
        for key in list(os.environ.keys()):
            if key.startswith('SAREMBOK_LOCAL_') or key in ('OPENROUTER_API_KEY', 'GEMINI_API_KEY', 'OPENAI_API_KEY', 'GROQ_API_KEY'):
                os.environ.pop(key, None)

    def test_local_only_mode_detection(self):
        router = ProviderRouter()
        self.assertFalse(router.is_local_only())
        self.assertFalse(router.is_local_only('gemini-flash'))
        self.assertTrue(router.is_local_only('local'))
        self.assertTrue(router.is_local_only('local-only'))
        self.assertTrue(router.is_local_only('local_only'))

        with patch.dict(os.environ, {'SAREMBOK_LOCAL_ONLY_MODE': 'true'}):
            r_local = ProviderRouter()
            self.assertTrue(r_local.is_local_only())
            self.assertTrue(r_local.is_local_only('gemini-flash'))

    def test_configured_in_local_only_mode_has_no_cloud_providers(self):
        with patch.dict(os.environ, {
            'SAREMBOK_LOCAL_ONLY_MODE': 'true',
            'SAREMBOK_LOCAL_GEMMA_URL': 'http://172.18.0.1:11434/v1/chat/completions',
            'SAREMBOK_LOCAL_GEMMA_MODEL': 'gemma2:2b',
            'GEMINI_API_KEY': 'AIzaTestGeminiKey',
            'OPENROUTER_API_KEY': 'sk-or-TestRouterKey',
            'OPENAI_API_KEY': 'sk-TestOpenAIKey',
        }):
            router = ProviderRouter()
            providers = router.configured()
            self.assertEqual(len(providers), 1)
            self.assertEqual(providers[0].name, 'LocalGemma')
            self.assertEqual(providers[0].model, 'gemma2:2b')
            self.assertEqual(providers[0].endpoint, 'http://172.18.0.1:11434/v1/chat/completions')
            # Verify ZERO cloud providers in list
            names = [p.name for p in providers]
            self.assertNotIn('Gemini', names)
            self.assertNotIn('OpenRouter', names)
            self.assertNotIn('OpenAI', names)

    def test_configured_preserves_production_defaults_when_local_only_false(self):
        with patch.dict(os.environ, {
            'SAREMBOK_LOCAL_ONLY_MODE': 'false',
            'GEMINI_API_KEY': 'AIzaTestGeminiKey',
            'OPENROUTER_API_KEY': 'sk-or-TestRouterKey',
        }):
            router = ProviderRouter()
            providers = router.configured()
            names = [p.name for p in providers]
            self.assertIn('Gemini', names)
            self.assertIn('OpenRouter', names)

    def test_local_only_mode_fails_cleanly_without_cloud_fallback(self):
        with patch.dict(os.environ, {
            'SAREMBOK_LOCAL_ONLY_MODE': 'true',
            'SAREMBOK_LOCAL_GEMMA_URL': 'http://127.0.0.1:9999/v1/chat/completions',  # Non-existent endpoint
            'GEMINI_API_KEY': 'AIzaTestGeminiKey',
            'OPENROUTER_API_KEY': 'sk-or-TestRouterKey',
        }):
            router = ProviderRouter()
            # Must raise RuntimeError with local_only_inference_failed and NEVER fall back to Gemini/OpenRouter
            with self.assertRaises(RuntimeError) as ctx:
                router.generate('You are a test assistant', 'Ping', [{'role': 'user', 'content': 'Ping'}])
            
            err_msg = str(ctx.exception)
            self.assertIn('local_only_inference_failed', err_msg)
            self.assertIn('LocalGemma failed', err_msg)
            self.assertIn('prohibited in local-only mode', err_msg)

    def test_bounded_context_and_max_tokens_for_local_model(self):
        router = ProviderRouter()
        spec = ProviderSpec('LocalGemma', 'gemma2:2b', 'openai', 'http://172.18.0.1:11434/v1/chat/completions', 'key')
        
        # Test max tokens bounded to 512
        payload = router._openai_payload(spec, [{'role': 'user', 'content': 'Hi'}])
        self.assertLessEqual(payload['max_tokens'], 512)

        # Test context truncation when content is excessively long
        long_text = 'A' * 20000
        messages = [
            {'role': 'system', 'content': 'System instruction'},
            {'role': 'user', 'content': long_text},
            {'role': 'assistant', 'content': 'Previous reply'},
            {'role': 'user', 'content': 'Recent query'},
        ]
        payload_long = router._openai_payload(spec, messages)
        total_chars = sum(len(str(m.get('content', ''))) for m in payload_long['messages'])
        self.assertLessEqual(total_chars, router.local_max_context_chars + 100)
        self.assertEqual(payload_long['messages'][0]['role'], 'system')


if __name__ == '__main__':
    unittest.main()
