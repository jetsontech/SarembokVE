import unittest

from sarembok_orchestrator import (
    OrchestrationContext,
    SarembokSystemOrchestrator,
    SystemEvent,
    SystemPhase,
)


class EchoComponent:
    def handle(self, context, event):
        return [SystemEvent("handled", "echo", {"phase": context.phase.value})]


class OrchestratorTests(unittest.TestCase):
    def test_event_is_dispatched_to_current_phase(self):
        orchestrator = SarembokSystemOrchestrator(
            {SystemPhase.OBSERVE: EchoComponent()}
        )
        result = orchestrator.process(
            OrchestrationContext("s1", "u1"),
            SystemEvent("screen.observed", "vision"),
        )
        self.assertEqual(result[0].payload["phase"], "observe")

    def test_context_can_advance_through_system_phases(self):
        context = OrchestrationContext("s2", "u2")
        context = SarembokSystemOrchestrator.advance(context, SystemPhase.PLAN)
        self.assertEqual(context.phase, SystemPhase.PLAN)

    def test_missing_component_fails_closed(self):
        orchestrator = SarembokSystemOrchestrator({})
        with self.assertRaises(RuntimeError):
            orchestrator.process(
                OrchestrationContext("s3", "u3"),
                SystemEvent("input", "user"),
            )


if __name__ == "__main__":
    unittest.main()
