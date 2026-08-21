"""Integration layer between SarembokAgent, memory, and the execution engine."""

from __future__ import annotations

import json
from typing import Any, Dict

from sarembok_agentic_execution import AgenticExecutionEngine, ExecutionLimits, ExecutionRecord, ExecutionState


class SarembokAgentRuntime:
    """Run agent work through bounded execution and persist the execution record."""

    def __init__(self, agent: Any, memory: Any, limits: ExecutionLimits | None = None):
        self.agent = agent
        self.memory = memory
        self.engine = AgenticExecutionEngine(limits)

    def handle_event(
        self,
        event: Dict[str, Any],
        execution_id: str,
        task_id: str = "event-task",
        agent_id: str = "sarembok-agent",
    ) -> ExecutionRecord:
        record = ExecutionRecord(execution_id, task_id, agent_id)

        def action(_record: ExecutionRecord) -> Any:
            return self.agent.process(event)

        result = self.engine.run(record, [action], lambda value, _record: isinstance(value, list))
        self._persist(record, event)
        return result

    def _persist(self, record: ExecutionRecord, event: Dict[str, Any]) -> None:
        self.memory.remember(
            f"execution:{record.execution_id}",
            json.dumps(
                {
                    "execution_id": record.execution_id,
                    "task_id": record.task_id,
                    "agent_id": record.agent_id,
                    "state": record.state.value,
                    "step": record.step,
                    "retries": record.retries,
                    "result": record.result,
                    "error": record.error,
                    "checkpoints": record.checkpoints,
                    "events": record.events,
                    "input_event": event,
                },
                default=str,
            ),
        )
        self.memory.remember("last_execution_id", record.execution_id)


__all__ = ["SarembokAgentRuntime", "ExecutionLimits", "ExecutionState"]
