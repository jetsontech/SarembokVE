"""Machine-readable response contract used alongside the human response."""
from __future__ import annotations

import re
from typing import Any


def _headings(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for line in text.splitlines()
        if (match := re.match(r"^#{1,3}\s+(.+)$", line.strip()))
    ]


def _code_blocks(text: str) -> list[dict[str, str]]:
    return [
        {"language": language or "code", "content": body.rstrip()}
        for language, body in re.findall(r"```([\w.+#-]*)\n([\s\S]*?)```", text)
    ]


def _bullets(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\s*[-*]\s+(.+)$", line)
        if match:
            items.append(match.group(1).strip())
    return items[:50]


def build_structured_response(
    text: str,
    *,
    action: dict[str, Any] | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: float | None = None,
    findings: list[dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
    agents: list[dict[str, Any]] | None = None,
    tasks: list[dict[str, Any]] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    authorization: list[dict[str, Any]] | None = None,
    verification: dict[str, Any] | None = None,
    memory_updates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    clean = str(text or "").strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", clean) if p.strip()]
    sections = [{"heading": heading} for heading in _headings(clean)]
    bullet_items = _bullets(clean)
    return {
        "type": "response",
        "speaker": "sarembok",
        "status": "complete",
        "content": {
            "summary": (paragraphs[0] if paragraphs else clean)[:500],
            "sections": sections,
            "findings": findings or [{"text": item} for item in bullet_items[:12]],
            "sources": sources or [],
            "agents": agents or [],
            "tasks": tasks or [],
            "artifacts": artifacts or [],
            "actions": [action] if action else [],
            "authorization": authorization or [],
            "verification": verification or {},
            "memoryUpdates": memory_updates or [],
            "code": _code_blocks(clean),
            "tables": [],
            "text": clean,
        },
        "metadata": {
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "schema_version": "2.0",
        },
    }
