import asyncio
import sqlite3
import unittest

from conversation_runtime import ConversationRuntime, ModelProvider


class FakeStore:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.events = []

    def event(self, agent_id, event_type, payload):
        self.events.append((agent_id, event_type, payload))


class ConversationRuntimeTests(unittest.TestCase):
    def test_response_text_extractors(self):
        self.assertEqual(
            ModelProvider._extract_text({"output_text": "hello"}),
            "hello",
        )
        self.assertEqual(
            ModelProvider._extract_text({
                "choices": [{"message": {"content": "chat hello"}}]
            }),
            "chat hello",
        )
        self.assertEqual(
            ModelProvider._extract_text({
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": "response hello"}],
                }]
            }),
            "response hello",
        )


    def test_deterministic_test_provider(self):
        import os

        previous = os.environ.get("SAREMBOK_MODEL_PROVIDER")

        try:
            os.environ["SAREMBOK_MODEL_PROVIDER"] = "test"

            store = FakeStore()
            runtime = ConversationRuntime(store)

            info = runtime.provider_info()

            self.assertEqual(info["provider"], "test")
            self.assertTrue(info["configured"])

            response = runtime.provider.complete([
                {
                    "role": "user",
                    "content": "Hello Sarembok",
                }
            ])

            self.assertEqual(
                response,
                "Sarembok test provider response: Hello Sarembok",
            )
        finally:
            if previous is None:
                os.environ.pop("SAREMBOK_MODEL_PROVIDER", None)
            else:
                os.environ["SAREMBOK_MODEL_PROVIDER"] = previous

    def test_chat_end_to_end_without_external_provider(self):
        import os

        previous = os.environ.get("SAREMBOK_MODEL_PROVIDER")

        try:
            os.environ["SAREMBOK_MODEL_PROVIDER"] = "test"

            store = FakeStore()
            runtime = ConversationRuntime(store)

            runtime.remember(
                "agent-test",
                "The user is validating Sarembok conversation runtime.",
                "test",
                1.0,
            )

            result = asyncio.run(
                runtime.chat(
                    "agent-test",
                    "Prove the conversation runtime works.",
                    asyncio.Lock(),
                    session_id="test-session",
                )
            )

            self.assertEqual(result["agentId"], "agent-test")
            self.assertEqual(result["sessionId"], "test-session")
            self.assertIn(
                "Prove the conversation runtime works.",
                result["content"],
            )
            self.assertEqual(result["memoryCount"], 1)
            self.assertEqual(
                runtime.history("agent-test")["count"],
                2,
            )
            self.assertTrue(
                any(
                    event[1] == "CHAT_COMPLETED"
                    for event in store.events
                )
            )
        finally:
            if previous is None:
                os.environ.pop("SAREMBOK_MODEL_PROVIDER", None)
            else:
                os.environ["SAREMBOK_MODEL_PROVIDER"] = previous

    def test_memory_and_chat_persistence(self):
        store = FakeStore()
        runtime = ConversationRuntime(store)
        runtime.provider.complete = lambda messages: "Hello from the model"

        stored = runtime.remember("agent-1", "The user prefers concise answers.", "preference", 0.9)
        self.assertEqual(stored["agentId"], "agent-1")

        result = asyncio.run(
            runtime.chat(
                "agent-1",
                "What do you remember?",
                asyncio.Lock(),
            )
        )

        self.assertEqual(result["content"], "Hello from the model")
        self.assertEqual(result["memoryCount"], 1)
        self.assertEqual(
            runtime.history("agent-1")["count"],
            2,
        )
        self.assertTrue(any(event[1] == "CHAT_COMPLETED" for event in store.events))


if __name__ == "__main__":
    unittest.main()


