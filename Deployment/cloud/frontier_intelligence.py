"""Frontier Intelligence routing and evidence formatting for Sarembok.

This layer decides when a natural-language request requires live research.
It deliberately does not treat an LLM's training memory as current evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

# Support both the production container and direct repository-root validation.
_RUNTIME_DIR = Path(__file__).resolve().parents[2] / "Runtime"
if str(_RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_DIR))

from sarembok_web_intelligence import research as web_research


LIVE_MARKERS = (
    "latest", "current", "today", "tonight", "this week", "this month",
    "recent", "newest", "new release", "recent release", "just released",
    "what happened", "news", "breaking", "developments", "research", "papers",
    "paper", "study", "studies", "benchmark", "benchmarks", "state of the art",
    "state-of-the-art", "frontier",
)

RESEARCH_DOMAINS = (
    "ai", "artificial intelligence", "machine learning", "llm", "language model",
    "agent", "agents", "model", "models", "computer use", "robotics",
    "generative ai", "genai", "mcp", "a2a", "webgpu", "w3c", "technology", "tech",
)


def is_live_research_intent(prompt: str) -> bool:
    """Return True when current external evidence is required."""
    text = " ".join(str(prompt or "").lower().split())
    if not text:
        return False
    return any(marker in text for marker in LIVE_MARKERS) and any(domain in text for domain in RESEARCH_DOMAINS)


def _topic(prompt: str) -> str:
    return " ".join(str(prompt or "").split()).strip() or "AI frontier developments"


def run(prompt: str, limit: int = 6) -> dict[str, Any]:
    """Execute bounded live research and return evidence suitable for the UI."""
    topic = _topic(prompt)
    started = datetime.now(timezone.utc)
    result = web_research(topic, limit=max(3, min(int(limit), 8)))
    retrieved = [item for item in result.get("evidence", []) if "error" not in item]
    failed = [item for item in result.get("evidence", []) if "error" in item]

    findings: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for item in retrieved:
        title = str(item.get("title") or "Untitled source").strip()
        excerpt = " ".join(str(item.get("excerpt") or "").split())
        if excerpt:
            findings.append({"title": title, "text": excerpt[:900], "url": item.get("url")})
        sources.append({"title": title, "url": item.get("url"), "status": item.get("status"), "contentType": item.get("contentType")})

    completed = datetime.now(timezone.utc)
    lines = [
        "# Frontier Intelligence Brief", "", f"**Query:** {topic}",
        f"**Retrieved:** {completed.isoformat()}",
        f"**Sources retrieved:** {len(retrieved)} · **Failed:** {len(failed)}", "", "## Evidence",
    ]
    if findings:
        for index, finding in enumerate(findings, 1):
            lines.extend(["", f"### {index}. {finding['title']}", "", finding["text"]])
    else:
        lines.extend(["", "No external evidence was successfully retrieved."])
    lines.extend([
        "", "## Research Integrity", "",
        "This response is based on live retrieval rather than model training-memory claims. "
        "Source retrieval time and URLs are preserved below for verification.",
    ])

    verification = {
        "status": "VERIFIED" if retrieved else "FAILED", "retrieved": len(retrieved),
        "failed": len(failed), "live": True, "startedAt": started.isoformat(),
        "completedAt": completed.isoformat(), "freshness": "live_retrieval",
    }
    text = "\n".join(lines)
    structured = {
        "type": "response", "speaker": "sarembok", "status": "complete" if retrieved else "error",
        "content": {
            "summary": f"Live frontier research retrieved {len(retrieved)} source(s) for: {topic}",
            "sections": [{"heading": "Frontier Intelligence Brief"}, {"heading": "Evidence"}, {"heading": "Research Integrity"}],
            "findings": findings, "sources": sources,
            "agents": [{"agentId": "sarembok-research", "role": "live-web-research"}],
            "tasks": [], "artifacts": [], "actions": [], "authorization": [],
            "verification": verification, "memoryUpdates": [], "code": [], "tables": [], "text": text,
        },
        "metadata": {"provider": "frontier-intelligence", "model": "live-web-research", "latency_ms": round((completed - started).total_seconds() * 1000, 1), "schema_version": "2.0"},
    }
    return {
        "response": text, "structuredResponse": structured,
        "source": "frontier-intelligence", "model": "live-web-research",
        "action": {"type": "LIVE_RESEARCH", "query": topic},
        "metadata": {"live": True, "retrieved": len(retrieved), "failed": len(failed)},
    }
