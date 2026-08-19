"""Adaptive workforce selection using observed agent fitness."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class CandidateAgent:
    agent_id: str
    capabilities: List[str]
    fitness_score: float


@dataclass(frozen=True)
class WorkforceSelection:
    capability: str
    agent_id: str
    fitness_score: float


class AdaptiveWorkforceOptimizer:
    """Selects the strongest eligible agent for each required capability."""

    def select(
        self,
        required_capabilities: List[str],
        candidates: List[CandidateAgent],
    ) -> List[WorkforceSelection]:
        selections: List[WorkforceSelection] = []
        for capability in required_capabilities:
            eligible = [
                candidate
                for candidate in candidates
                if capability in candidate.capabilities
            ]
            if not eligible:
                raise RuntimeError(f"no_eligible_agent:{capability}")
            best = max(eligible, key=lambda candidate: candidate.fitness_score)
            selections.append(
                WorkforceSelection(capability, best.agent_id, best.fitness_score)
            )
        return selections
