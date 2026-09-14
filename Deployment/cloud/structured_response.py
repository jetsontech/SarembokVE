"""Machine-readable response contract used alongside the human response."""
from __future__ import annotations

import re
from typing import Any


def _unescape_markdown(text: str) -> str:
    return re.sub(r"\\([\\`*_|~#+>~-])", r"\1", text)


def _parse_tables(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    tables: list[dict[str, Any]] = []
    i = 0

    while i + 1 < len(lines):
        header = lines[i].strip()
        separator = lines[i + 1].strip()

        if (
            header.startswith("|")
            and header.endswith("|")
            and re.match(r"^\|?[\s:|-]+\|[\s:|:-]*$", separator)
        ):
            header_cells = [
                _unescape_markdown(c.strip())
                for c in header.strip("|").split("|")
            ]

            align_cells = [
                c.strip()
                for c in separator.strip("|").split("|")
            ]

            rows: list[list[str]] = []
            j = i + 2

            while j < len(lines):
                row = lines[j].strip()
                if not (row.startswith("|") and row.endswith("|")):
                    break

                cells = [
                    _unescape_markdown(c.strip())
                    for c in row.strip("|").split("|")
                ]
                rows.append(cells)
                j += 1

            tables.append({
                "headers": header_cells,
                "rows": rows,
                "align": [
                    (
                        "center" if c.startswith(":") and c.endswith(":")
                        else "left" if not c.endswith(":")
                        else "right"
                    )
                    for c in align_cells
                ],
            })

            i = j
            continue

        i += 1

    return tables


def build_structured_response(
    text: str,
    *,
    action: dict[str, Any] | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: float | None = None,
) -> dict[str, Any]:
    clean = str(text or "").strip()

    normalized = _unescape_markdown(clean)
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", normalized)
        if p.strip()
    ]

    headings = []
    for line in normalized.splitlines():
        m = re.match(r"^#{1,3}\s+(.+)$", line.strip())
        if m:
            headings.append(m.group(1).strip())

    code = [
        {
            "language": lang or "code",
            "content": body.rstrip(),
        }
        for lang, body in re.findall(
            r"```([\w.+#-]*)\n([\s\S]*?)```",
            clean,
        )
    ]

    tables = _parse_tables(clean)

    return {
        "type": "response",
        "speaker": "sarembok",
        "status": "complete",
        "content": {
            "summary": (paragraphs[0] if paragraphs else normalized)[:500],
            "sections": [{"heading": h} for h in headings],
            "actions": [action] if action else [],
            "code": code,
            "tables": tables,
            "sources": [],
            "text": clean,
        },
        "metadata": {
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "schema_version": "1.1",
        },
    }
