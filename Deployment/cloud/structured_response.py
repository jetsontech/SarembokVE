"""Machine-readable response contract used alongside the human response."""
from __future__ import annotations
import re
from typing import Any

def build_structured_response(text: str, *, action: dict[str, Any] | None = None, provider: str | None = None, model: str | None = None, latency_ms: float | None = None) -> dict[str, Any]:
    clean = str(text or '').strip()
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', clean) if p.strip()]
    headings = []
    for line in clean.splitlines():
        m = re.match(r'^#{1,3}\s+(.+)$', line.strip())
        if m: headings.append(m.group(1).strip())
    code = [{'language': lang or 'code', 'content': body.rstrip()} for lang, body in re.findall(r'```([\w.+#-]*)\n([\s\S]*?)```', clean)]
    return {'type':'response','speaker':'sarembok','status':'complete','content':{'summary':(paragraphs[0] if paragraphs else clean)[:500],'sections':[{'heading':h} for h in headings],'actions':[action] if action else [],'code':code,'tables':[],'sources':[],'text':clean},'metadata':{'provider':provider,'model':model,'latency_ms':latency_ms,'schema_version':'1.0'}}
