import unittest

from sarembok_agent_registry import (
    AgentFactory,
    AgentLifecycle,
    AgentRegistry,
    AgentSpecification,
    RegisteredAgent,
)


class FakeFactory:
    def create(self, agent_id, specification):
        return RegisteredAgent(agent_id, specification, AgentLifecycle.READY)


class AgentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry(FakeFactory())

    def test_dynamic_agent_creation_registers_agent(self):
        agent = self.registry.create(
            "research-1",
            AgentSpecification("research", ["web_research", "synthesis"]),
        )
        self.assertEqual(agent.lifecycle, AgentLifecycle.READY)
        self.assertEqual(self.registry.get("research-1").agent_id, "research-1")

    def test_capability_discovery_finds_non_retired_agents(self):
        self.registry.register(
            RegisteredAgent(
                "vision-1",
                AgentSpecification("vision", ["image_analysis"]),
                AgentLifecycle.ACTIVE,
            )
        )
        matches = self.registry.find_by_capability("image_analysis")
        self.assertEqual([a.agent_id for a in matches], ["vision-1"])

    def test_duplicate_creation_fails_closed(self):
        spec = AgentSpecification("coding", ["python"])
        self.registry.create("coder-1", spec)
        with self.assertRaises(RuntimeError):
            self.registry.create("coder-1", spec)

    def test_activation_changes_lifecycle(self):
        agent = self.registry.create("worker-1", AgentSpecification("execution"))
        active = self.registry.activate(agent.agent_id)
        self.assertEqual(active.lifecycle, AgentLifecycle.ACTIVE)


if __name__ == "__main__":
    unittest.main()
