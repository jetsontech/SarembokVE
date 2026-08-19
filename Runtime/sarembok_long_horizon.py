"""Long-horizon autonomous task primitives for Sarembok.

Tracks durable task state, explicit horizons, checkpoints, recovery attempts,
and multi-step progress without coupling the engine to a particular model or
execution provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    CHECKPOINTED = "checkpointed"
    WAITING = "waiting"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class AgenticHorizon:
    max_duration_seconds: int
    max_steps: int
    checkpoint_every_steps: int = 5
    max_recovery_attempts: int = 3


@dataclass(frozen=True)
class TaskCheckpoint:
    checkpoint_id: str
    step: int
    state: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AutonomousTask:
    task_id: str
    goal: str
    horizon: AgenticHorizon
    status: TaskStatus = TaskStatus.PLANNED
    current_step: int = 0
    recovery_attempts: int = 0
    checkpoint: Optional[TaskCheckpoint] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LongHorizonTaskEngine:
    """Pure state-transition engine; execution remains an external adapter."""

    def start(self, task: AutonomousTask) -> AutonomousTask:
        if task.status not in {TaskStatus.PLANNED, TaskStatus.CHECKPOINTED, TaskStatus.RECOVERING}:
            raise RuntimeError(f"cannot_start:{task.status.value}")
        return replace(task, status=TaskStatus.RUNNING)

    def advance(self, task: AutonomousTask, state: Optional[Dict[str, Any]] = None) -> AutonomousTask:
        if task.status != TaskStatus.RUNNING:
            raise RuntimeError(f"cannot_advance:{task.status.value}")
        next_step = task.current_step + 1
        if next_step > task.horizon.max_steps:
            return replace(task, status=TaskStatus.FAILED)
        checkpoint = task.checkpoint
        status = TaskStatus.RUNNING
        if next_step % task.horizon.checkpoint_every_steps == 0:
            checkpoint = TaskCheckpoint(f"{task.task_id}:{next_step}", next_step, state or {})
            status = TaskStatus.CHECKPOINTED
        return replace(task, current_step=next_step, checkpoint=checkpoint, status=status)

    def recover(self, task: AutonomousTask) -> AutonomousTask:
        if task.recovery_attempts >= task.horizon.max_recovery_attempts:
            return replace(task, status=TaskStatus.FAILED)
        if task.checkpoint is None:
            return replace(task, status=TaskStatus.FAILED)
        return replace(
            task,
            status=TaskStatus.RECOVERING,
            recovery_attempts=task.recovery_attempts + 1,
            current_step=task.checkpoint.step,
        )

    def complete(self, task: AutonomousTask) -> AutonomousTask:
        if task.status not in {TaskStatus.RUNNING, TaskStatus.CHECKPOINTED}:
            raise RuntimeError(f"cannot_complete:{task.status.value}")
        return replace(task, status=TaskStatus.COMPLETED)
