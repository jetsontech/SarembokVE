"""Evidence-based agent performance evaluation for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, List


@dataclass(frozen=True)
class AgentPerformanceRecord:
    agent_id: str
    success: bool
    latency_seconds: float
    resource_units: float = 0.0
    verification_score: float = 0.0


@dataclass(frozen=True)
class AgentFitness:
    agent_id: str
    success_rate: float
    average_latency_seconds: float
    average_resource_units: float
    average_verification_score: float
    fitness_score: float


class AgentPerformanceEvaluator:
    """Turns observed task outcomes into deterministic agent fitness metrics."""

    def __init__(self, records: List[AgentPerformanceRecord] | None = None):
        self.records = list(records or [])

    def record(self, result: AgentPerformanceRecord) -> None:
        if result.latency_seconds < 0 or result.resource_units < 0:
            raise ValueError("performance_metrics_must_be_non_negative")
        if not 0.0 <= result.verification_score <= 1.0:
            raise ValueError("verification_score_must_be_between_zero_and_one")
        self.records.append(result)

    def evaluate(self, agent_id: str) -> AgentFitness:
        records = [r for r in self.records if r.agent_id == agent_id]
        if not records:
            raise RuntimeError(f"no_performance_history:{agent_id}")
        success_rate = sum(r.success for r in records) / len(records)
        latency = mean(r.latency_seconds for r in records)
        resources = mean(r.resource_units for r in records)
        verification = mean(r.verification_score for r in records)
        # Higher is better. Latency/resource penalties are bounded by normalization.
        efficiency = 1.0 / (1.0 + latency + resources)
        fitness = (success_rate * 0.45) + (verification * 0.40) + (efficiency * 0.15)
        return AgentFitness(agent_id, success_rate, latency, resources, verification, fitness)

    def rank(self, agent_ids: List[str]) -> List[AgentFitness]:
        return sorted((self.evaluate(agent_id) for agent_id in agent_ids), key=lambda x: x.fitness_score, reverse=True)
