import unittest

from sarembok_knowledge_transfer import CrossAgentKnowledgeBase, KnowledgeArtifact


class KnowledgeTransferTests(unittest.TestCase):
    def setUp(self):
        self.knowledge = CrossAgentKnowledgeBase()

    def test_publish_and_share_knowledge(self):
        self.knowledge.publish(
            KnowledgeArtifact(
                "k1", "agent-a", "use contract tests", "contract-first",
                capabilities=["coding"], confidence=0.95,
            )
        )
        matches = self.knowledge.share("agent-b", capability="coding")
        self.assertEqual(matches[0].knowledge_id, "k1")
        self.assertEqual(matches[0].source_agent_id, "agent-a")

    def test_confidence_and_identity_are_validated(self):
        with self.assertRaises(ValueError):
            self.knowledge.publish(KnowledgeArtifact("k1", "", "lesson"))
        with self.assertRaises(ValueError):
            self.knowledge.publish(KnowledgeArtifact("k2", "agent-a", "lesson", confidence=1.1))

    def test_duplicate_knowledge_fails_closed(self):
        artifact = KnowledgeArtifact("k1", "agent-a", "lesson")
        self.knowledge.publish(artifact)
        with self.assertRaises(RuntimeError):
            self.knowledge.publish(artifact)

    def test_share_requires_target_and_positive_limit(self):
        with self.assertRaises(ValueError):
            self.knowledge.share("")
        with self.assertRaises(ValueError):
            self.knowledge.share("agent-b", limit=0)


if __name__ == "__main__":
    unittest.main()
