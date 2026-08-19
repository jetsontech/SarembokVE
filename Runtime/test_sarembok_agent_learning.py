import unittest

from sarembok_agent_learning import AgentExperience, AgentLearningMemory


class AgentLearningTests(unittest.TestCase):
    def setUp(self):
        self.memory = AgentLearningMemory()

    def test_remember_and_recall_experience(self):
        self.memory.remember(
            AgentExperience("exp-1", "agent-1", "task-1", "success", "tests first", "test-first", tags=["coding"])
        )
        results = self.memory.recall("agent-1", "coding")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].lesson, "tests first")

    def test_learning_separates_successful_and_failed_strategies(self):
        self.memory.remember(AgentExperience("exp-1", "agent-1", "task-1", "success", "use tests", "test-first"))
        self.memory.remember(AgentExperience("exp-2", "agent-1", "task-2", "failure", "avoid guessing", "guess-first"))
        learning = self.memory.learn("agent-1")
        self.assertEqual(learning.successful_strategies, ["test-first"])
        self.assertEqual(learning.failed_strategies, ["guess-first"])
        self.assertEqual(learning.experience_count, 2)

    def test_duplicate_experience_fails_closed(self):
        experience = AgentExperience("exp-1", "agent-1", "task-1", "success", "lesson")
        self.memory.remember(experience)
        with self.assertRaises(RuntimeError):
            self.memory.remember(experience)

    def test_invalid_experience_fails_closed(self):
        with self.assertRaises(ValueError):
            self.memory.remember(AgentExperience("exp-1", "", "task-1", "success", "lesson"))


if __name__ == "__main__":
    unittest.main()
