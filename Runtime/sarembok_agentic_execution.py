"""Minimal provider-neutral agentic execution engine for Sarembok.

This module owns execution state and bounded control flow. Model providers and
computer/device capabilities are adapters supplied by callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Any, Callable, Dict, List, Optional


class ExecutionState(str, Enum):
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VALIDATING = "VALIDATING"
    CHECKPOINTED = "CHECKPOINTED"
    RECOVERY = "RECOVERY"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ExecutionLimits:
    max_time_seconds: float = 300.0
    max_steps: int = 50
    checkpoint_interval: int = 5
    max_retries: int = 2


@dataclass
class ExecutionRecord:
    execution_id: str
    task_id: str
    agent_id: str
    state: ExecutionState = ExecutionState.QUEUED
    step: int = 0
    retries: int = 0
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None

    def event(self, kind: str, **data: Any) -> None:
        self.events.append({"step": self.step, "kind": kind, **data})


class AgenticExecutionEngine:
    """Execute bounded actions while preserving inspectable state."""

    def __init__(self, limits: Optional[ExecutionLimits] = None) -> None:
        self.limits = limits or ExecutionLimits()

    def run(
        self,
        record: ExecutionRecord,
        actions: List[Callable[[ExecutionRecord], Any]],
        validate: Callable[[Any, ExecutionRecord], bool],
    ) -> ExecutionRecord:
        started = monotonic()
        record.state = ExecutionState.PLANNING
        record.event("planning_started", action_count=len(actions))

        if not actions:
            record.state = ExecutionState.COMPLETED
            record.result = None
            record.event("completed", reason="no_actions")
            return record

        for action in actions:
            if record.step >= self.limits.max_steps:
                return self._escalate(record, "max_steps_exceeded")
            if monotonic() - started >= self.limits.max_time_seconds:
                return self._escalate(record, "max_time_exceeded")

            record.step += 1
            record.state = ExecutionState.EXECUTING
            record.event("action_started", action=getattr(action, "__name__", "callable"))

            try:
                result = action(record)
                record.state = ExecutionState.OBSERVING
                record.event("observation", result=result)
                record.state = ExecutionState.VALIDATING

                if not validate(result, record):
                    raise RuntimeError("action_validation_failed")

                record.result = result
                record.event("validation_passed")
                self._checkpoint_if_due(record)
            except Exception as exc:  # bounded recovery; caller owns policy.
                record.retries += 1
                record.error = str(exc)
                record.event("action_failed", error=str(exc), retry=record.retries)
                if record.retries > self.limits.max_retries:
                    record.state = ExecutionState.FAILED
                    return record
                record.state = ExecutionState.RECOVERY
                self._checkpoint(record, reason="recovery")

        record.state = ExecutionState.COMPLETED
        record.event("completed")
        self._checkpoint(record, reason="completed")
        return record

    def _checkpoint_if_due(self, record: ExecutionRecord) -> None:
        if record.step % max(1, self.limits.checkpoint_interval) == 0:
            self._checkpoint(record, reason="interval")

    @staticmethod
    def _checkpoint(record: ExecutionRecord, reason: str) -> None:
        record.state = ExecutionState.CHECKPOINTED
        record.checkpoints.append(
            {"step": record.step, "reason": reason, "result": record.result}
        )
        record.event("checkpoint", reason=reason)

    @staticmethod
    def _escalate(record: ExecutionRecord, reason: str) -> ExecutionRecord:
        record.error = reason
        record.state = ExecutionState.ESCALATED
        record.event("escalated", reason=reason)
        return record
