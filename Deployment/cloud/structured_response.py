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


def _sections_with_text(text: str) -> list[dict[str, str]]:
    """Preserve heading/body relationships for renderers that consume findings."""
    sections: list[dict[str, str]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_body
        if current_heading:
            detail = "\n\n".join(current_body).strip()
            sections.append({"heading": current_heading, "text": detail})
        current_heading = None
        current_body = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^#{1,3}\s+(.+)$", line)
        if match:
            flush()
            current_heading = match.group(1).strip()
            continue
        if current_heading and line:
            current_body.append(line)

    flush()
    return sections[:20]


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
    sections = _sections_with_text(clean)
    bullet_items = _bullets(clean)

    if findings is not None:
        structured_findings = findings
    elif bullet_items:
        structured_findings = [{"text": item} for item in bullet_items[:12]]
    else:
        structured_findings = [
            {"title": section["heading"], "detail": section["text"]}
            for section in sections
            if section.get("text")
        ][:12]

    # A heading-only first paragraph is not useful as the response summary.
    # Prefer the first substantive body paragraph so the UI never renders
    # only a section title while hiding the model's actual answer.
    body_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if not re.match(r"^#{1,3}\s+", paragraph)
    ]
    summary_source = body_paragraphs[0] if body_paragraphs else (paragraphs[0] if paragraphs else clean)

    return {
        "type": "response",
        "speaker": "sarembok",
        "status": "complete",
        "content": {
            "summary": summary_source[:500],
            "sections": sections,
            "findings": structured_findings,
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
