import unittest

from sarembok_agent_learning import AgentExperience
from sarembok_contextual_memory import ContextualMemoryRetriever, MemoryQuery


class ContextualMemoryTests(unittest.TestCase):
    def setUp(self):
        self.retriever = ContextualMemoryRetriever()
        self.experiences = [
            AgentExperience("e1", "agent-1", "t1", "success", "use tests before coding", "test-first", tags=["coding"]),
            AgentExperience("e2", "agent-2", "t2", "failure", "avoid guessing dependencies", "dependency-check", tags=["coding"]),
        ]

    def test_retrieval_ranks_contextually_relevant_memory(self):
        matches = self.retriever.search(MemoryQuery("coding tests", "coding", ["coding"]), self.experiences)
        self.assertEqual(matches[0].experience_id, "e1")

    def test_limit_is_respected(self):
        matches = self.retriever.search(MemoryQuery("coding"), self.experiences, limit=1)
        self.assertEqual(len(matches), 1)

    def test_invalid_limit_fails_closed(self):
        with self.assertRaises(ValueError):
            self.retriever.search(MemoryQuery("coding"), self.experiences, limit=0)


if __name__ == "__main__":
    unittest.main()
