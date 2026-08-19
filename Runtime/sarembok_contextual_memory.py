"""Contextual retrieval over Sarembok agent experience memory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class MemoryQuery:
    task_text: str
    capability: str = ""
    tags: List[str] = None


@dataclass(frozen=True)
class MemoryMatch:
    experience_id: str
    agent_id: str
    score: float
    lesson: str
    strategy: str


class ContextualMemoryRetriever:
    """Ranks prior experiences using simple deterministic contextual overlap."""

    def search(self, query: MemoryQuery, experiences: List[object], limit: int = 5) -> List[MemoryMatch]:
        if limit < 1:
            raise ValueError("limit_must_be_positive")
        query_terms = set(query.task_text.lower().split())
        query_tags = set(query.tags or [])
        matches: List[MemoryMatch] = []
        for experience in experiences:
            text = f"{experience.lesson} {experience.strategy}".lower()
            text_terms = set(text.split())
            overlap = len(query_terms & text_terms)
            tag_overlap = len(query_tags & set(getattr(experience, "tags", [])))
            score = float(overlap) + float(tag_overlap)
            if query.capability and query.capability in getattr(experience, "tags", []):
                score += 2.0
            if score > 0:
                matches.append(MemoryMatch(experience.experience_id, experience.agent_id, score, experience.lesson, experience.strategy))
        return sorted(matches, key=lambda item: (-item.score, item.experience_id))[:limit]
