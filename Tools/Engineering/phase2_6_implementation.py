from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / 'Deployment' / 'cloud' / 'server.py'
COMPOSE = ROOT / 'Deployment' / 'cloud' / 'compose.production.yaml'

PROVIDER = '''"""Sarembok provider routing and latency telemetry."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any


TRANSIENT_HTTP = {408, 429, 500, 502, 503, 504}

@dataclass(frozen=True)
class ProviderSpec:
    name: str
    model: str
    kind: str
    endpoint: str
    key: str

@dataclass
class ProviderResult:
    text: str
    provider: str
    model: str
    latency_ms: float
    attempts: int
    api: str
    usage: dict[str, Any] = field(default_factory=dict)

class ProviderRouter:
    def __init__(self) -> None:
        self.provider_timeout = max(5, int(os.getenv('SAREMBOK_LLM_PROVIDER_TIMEOUT_SECONDS', '20')))
        self.total_timeout = max(5, int(os.getenv('SAREMBOK_LLM_TOTAL_TIMEOUT_SECONDS', '30')))
        self.gemini_api = os.getenv('SAREMBOK_GEMINI_API', 'interactions').strip().lower()
        self.gemini_thinking = os.getenv('SAREMBOK_GEMINI_THINKING_LEVEL', 'low').strip().lower()
        if self.gemini_thinking not in {'low', 'medium', 'high'}:
            self.gemini_thinking = 'low'
        self.max_output_tokens = max(64, int(os.getenv('SAREMBOK_LLM_MAX_OUTPUT_TOKENS', '800')))
        self._history: deque[dict[str, Any]] = deque(maxlen=200)

    def configured(self) -> list[ProviderSpec]:
        result: dict[str, ProviderSpec] = {}
        openai = os.getenv('OPENAI_API_KEY', '').strip()
        if openai:
            result['OpenAI'] = ProviderSpec('OpenAI', os.getenv('LLM_MODEL', 'gpt-5-mini'), 'openai', 'https://api.openai.com/v1/chat/completions', openai)
        router = os.getenv('OPENROUTER_API_KEY', '').strip()
        if router:
            result['OpenRouter'] = ProviderSpec('OpenRouter', os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-120b'), 'openai', 'https://openrouter.ai/api/v1/chat/completions', router)
        groq = os.getenv('GROQ_API_KEY', '').strip()
        if groq:
            result['Groq'] = ProviderSpec('Groq', os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b'), 'openai', 'https://api.groq.com/openai/v1/chat/completions', groq)
        gemini = os.getenv('GEMINI_API_KEY', '').strip()
        if gemini:
            result['Gemini'] = ProviderSpec('Gemini', os.getenv('GEMINI_MODEL', 'gemini-3.8-flash'), 'gemini', 'https://generativelanguage.googleapis.com/v1beta/interactions', gemini)
        custom = os.getenv('LLM_ENDPOINT_URL', '').strip()
        if custom:
            result['Custom'] = ProviderSpec('Custom', os.getenv('LLM_MODEL', 'llama-3.1-8b'), 'openai', custom, os.getenv('LLM_API_KEY', 'dummy'))
        order = [x.strip() for x in os.getenv('SAREMBOK_PROVIDER_ORDER', 'Gemini,OpenRouter,Groq,OpenAI,Custom').split(',') if x.strip()]
        return [result[x] for x in order if x in result] + [v for k, v in result.items() if k not in order]

    @staticmethod
    def _extract_gemini(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        parts: list[str] = []
        for step in payload.get('steps', []) or []:
            if step.get('type') != 'model_output':
                continue
            for block in step.get('content', []) or []:
                if block.get('type') == 'text' and block.get('text'):
                    parts.append(block['text'])
        if not parts:
            # Compatibility with generateContent-shaped responses.
            for cand in payload.get('candidates', []) or []:
                for part in cand.get('content', {}).get('parts', []) or []:
                    if part.get('text'):
                        parts.append(part['text'])
        if not parts:
            raise RuntimeError('Gemini returned no model output')
        return ''.join(parts).strip(), payload.get('usage', {}) or {}

    def _request(self, spec: ProviderSpec, system_prompt: str, prompt: str, messages: list[dict[str, str]], deadline: float) -> tuple[str, dict[str, Any], str]:
        if spec.kind == 'gemini':
            if self.gemini_api == 'generatecontent':
                url = f'https://generativelanguage.googleapis.com/v1beta/models/{spec.model}:generateContent'
                data = {'system_instruction': {'parts': [{'text': system_prompt}]}, 'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': {'maxOutputTokens': self.max_output_tokens}}
                headers = {'Content-Type': 'application/json', 'x-goog-api-key': spec.key}
                api_name = 'generateContent'
            else:
                url = spec.endpoint
                data = {'model': spec.model, 'system_instruction': system_prompt, 'input': prompt, 'store': False, 'generation_config': {'thinking_level': self.gemini_thinking, 'max_output_tokens': self.max_output_tokens}}
                headers = {'Content-Type': 'application/json', 'x-goog-api-key': spec.key}
                api_name = 'interactions'
        else:
            url = spec.endpoint
            data = {'model': spec.model, 'messages': messages, 'max_tokens': self.max_output_tokens, 'temperature': 0.7}
            headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {spec.key}'}
            if spec.name == 'OpenRouter':
                headers.update({'HTTP-Referer': 'https://sarembok.com', 'X-Title': 'Sarembok VE'})
            api_name = 'chat.completions'
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        attempts = 0
        while True:
            attempts += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('provider deadline exceeded')
            timeout = min(self.provider_timeout, max(1, remaining))
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    payload = json.loads(response.read().decode('utf-8'))
                if spec.kind == 'gemini':
                    text, usage = self._extract_gemini(payload)
                else:
                    text = str(payload['choices'][0]['message']['content']).strip()
                    usage = payload.get('usage', {}) or {}
                return text, usage, api_name
            except urllib.error.HTTPError as exc:
                if exc.code not in TRANSIENT_HTTP or attempts >= 2:
                    raise
                delay = min(1.5, 0.35 * (2 ** (attempts - 1)))
                if deadline - time.monotonic() <= delay + 1:
                    raise
                time.sleep(delay)

    def generate(self, system_prompt: str, prompt: str, messages: list[dict[str, str]]) -> ProviderResult:
        providers = self.configured()
        if not providers:
            raise RuntimeError('no language-model provider configured')
        deadline = time.monotonic() + self.total_timeout
        failures: list[str] = []
        for spec in providers:
            started = time.monotonic()
            try:
                text, usage, api_name = self._request(spec, system_prompt, prompt, messages, deadline)
                latency_ms = round((time.monotonic() - started) * 1000, 1)
                record = {'provider': spec.name, 'model': spec.model, 'latency_ms': latency_ms, 'attempts': 1, 'api': api_name, 'ok': True, 'timestamp': time.time()}
                self._history.append(record)
                return ProviderResult(text, spec.name, spec.model, latency_ms, 1, api_name, usage)
            except Exception as exc:
                latency_ms = round((time.monotonic() - started) * 1000, 1)
                failures.append(f'{spec.name}:{type(exc).__name__}')
                self._history.append({'provider': spec.name, 'model': spec.model, 'latency_ms': latency_ms, 'attempts': 1, 'api': self.gemini_api if spec.kind == 'gemini' else 'chat.completions', 'ok': False, 'error': type(exc).__name__, 'timestamp': time.time()})
        raise RuntimeError('all providers failed: ' + ','.join(failures))

    def metrics(self) -> dict[str, Any]:
        entries = list(self._history)
        ok = [e for e in entries if e.get('ok')]
        return {'configuredProviders': [{'name': p.name, 'model': p.model, 'api': self.gemini_api if p.kind == 'gemini' else 'chat.completions'} for p in self.configured()], 'samples': len(entries), 'successes': len(ok), 'failures': len(entries) - len(ok), 'recent': entries[-20:]}
'''
CAPS = '''"""Truthful runtime capability registry for Sarembok."""
from __future__ import annotations
import os
from typing import Any

RPC_CAPABILITIES = {
    'SarembokChat': ('dialogue', 'Interactive Sarembok dialogue through the configured provider fabric.'),
    'GetRuntimeInfo': ('runtime', 'Read-only runtime health and system counts.'),
    'GetConversationHistory': ('memory', 'Read conversation history for a session.'),
    'CreateAgent': ('agents', 'Register an agent in the runtime.'),
    'QueryAgentState': ('agents', 'Read registered agent state.'),
    'InjectPerception': ('perception', 'Inject perception events for a registered agent.'),
    'EvaluateDecision': ('governance', 'Evaluate a decision through the runtime policy boundary.'),
    'GetCognitiveScorecard': ('evaluation', 'Read the runtime cognitive scorecard.'),
    'QueryWorldModel': ('world-model', 'Query the current world-model surface.'),
    'CreateDelegation': ('agents', 'Create an agent delegation record.'),
    'GetAuditTrail': ('governance', 'Read an agent audit trail.'),
    'SendMessage': ('messaging', 'Send a message to a registered agent.'),
    'GetEvents': ('events', 'Read agent events.'),
    'GetMetrics': ('observability', 'Read agent metrics.'),
    'RestoreState': ('persistence', 'Record a state-restore operation.'),
    'RegisterWorker': ('compute', 'Register a compute worker.'),
    'ListWorkers': ('compute', 'List registered workers and their liveness.'),
    'Heartbeat': ('compute', 'Update a worker heartbeat.'),
    'CreateTask': ('scheduler', 'Create a scheduled compute task.'),
    'ClaimTask': ('scheduler', 'Claim a queued task on an eligible worker.'),
    'CompleteTask': ('scheduler', 'Complete a running worker task.'),
    'FailTask': ('scheduler', 'Fail or retry a worker task.'),
    'RuntimeInfo': ('runtime', 'Read the extended runtime information surface.'),
    'ListProjects': ('projects', 'List runtime projects.'),
    'CreateProject': ('projects', 'Create a runtime project.'),
}

class CapabilityRegistry:
    def snapshot(self, runtime_state: dict[str, Any] | None = None) -> dict[str, Any]:
        providers = []
        for name, key, model in [('OpenAI','OPENAI_API_KEY',os.getenv('LLM_MODEL','gpt-5-mini')),('OpenRouter','OPENROUTER_API_KEY',os.getenv('OPENROUTER_MODEL','openai/gpt-oss-120b')),('Groq','GROQ_API_KEY',os.getenv('GROQ_MODEL','openai/gpt-oss-120b')),('Gemini','GEMINI_API_KEY',os.getenv('GEMINI_MODEL','gemini-3.8-flash')),('Custom','LLM_ENDPOINT_URL',os.getenv('LLM_MODEL','custom'))]:
            if os.getenv(key): providers.append({'name': name, 'model': model, 'configured': True})
        return {'registryVersion':'1.0', 'capabilities':[{'method':m,'domain':d,'description':desc,'enabled':True} for m,(d,desc) in RPC_CAPABILITIES.items()], 'providers':providers, 'runtime':runtime_state or {}}
'''
STRUCT = '''"""Machine-readable response contract used alongside the human response."""
from __future__ import annotations
import re
from typing import Any

def build_structured_response(text: str, *, action: dict[str, Any] | None = None, provider: str | None = None, model: str | None = None, latency_ms: float | None = None) -> dict[str, Any]:
    clean = str(text or '').strip()
    paragraphs = [p.strip() for p in re.split(r'\\n\\s*\\n', clean) if p.strip()]
    headings = []
    for line in clean.splitlines():
        m = re.match(r'^#{1,3}\\s+(.+)$', line.strip())
        if m: headings.append(m.group(1).strip())
    code = [{'language': lang or 'code', 'content': body.rstrip()} for lang, body in re.findall(r'```([\\w.+#-]*)\\n([\\s\\S]*?)```', clean)]
    return {'type':'response','speaker':'sarembok','status':'complete','content':{'summary':(paragraphs[0] if paragraphs else clean)[:500],'sections':[{'heading':h} for h in headings],'actions':[action] if action else [],'code':code,'tables':[],'sources':[],'text':clean},'metadata':{'provider':provider,'model':model,'latency_ms':latency_ms,'schema_version':'1.0'}}
'''

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

write(ROOT/'Deployment/cloud/provider_router.py', PROVIDER)
write(ROOT/'Deployment/cloud/capability_registry.py', CAPS)
write(ROOT/'Deployment/cloud/structured_response.py', STRUCT)

s = SERVER.read_text(encoding='utf-8')
s = s.replace('import uuid\n', 'import uuid\n\nfrom provider_router import ProviderRouter\nfrom capability_registry import CapabilityRegistry\nfrom structured_response import build_structured_response\n')
s = s.replace('STARTED = time.time()\n', 'STARTED = time.time()\nPROVIDER_ROUTER = ProviderRouter()\nCAPABILITY_REGISTRY = CapabilityRegistry()\n')
start = s.index('    reply = None\n    source = None\n    model = None\n    provider_deadline = time.monotonic() + LLM_TOTAL_TIMEOUT_SECONDS\n')
end = s.index('\n    if reply is not None:', start)
replacement = '''    reply = None\n    source = None\n    model = None\n    provider_latency_ms = None\n    provider_api = None\n    provider_usage = {}\n    try:\n        provider_result = PROVIDER_ROUTER.generate(system_prompt, prompt_clean, messages)\n        reply = provider_result.text\n        source = provider_result.provider\n        model = provider_result.model\n        provider_latency_ms = provider_result.latency_ms\n        provider_api = provider_result.api\n        provider_usage = provider_result.usage\n    except Exception as exc:\n        LOG.warning("LLM provider fabric failed: %s", exc)\n'''
s = s[:start] + replacement + s[end:]
s = s.replace('return {"response": reply, "audioText": reply[:300].replace("*", "").replace("`", "").replace("#", ""), "source": source, "model": model, "action": None}', 'return {"response": reply, "audioText": reply[:300].replace("*", "").replace("`", "").replace("#", ""), "source": source, "model": model, "action": None, "structuredResponse": build_structured_response(reply, provider=source, model=model, latency_ms=provider_latency_ms), "metadata": {"provider": source, "model": model, "latency_ms": provider_latency_ms, "provider_api": provider_api, "usage": provider_usage}}')
marker = '    if method == "GetRuntimeInfo":\n'
cap = '''    if method == "GetCapabilities":\n        worker_stats = get_worker_status_counts()\n        runtime_state = {"onlineWorkers": worker_stats["onlineWorkers"], "registeredWorkers": worker_stats["registeredWorkers"], "llmConfigured": bool(PROVIDER_ROUTER.configured())}\n        return CAPABILITY_REGISTRY.snapshot(runtime_state)\n\n    if method == "GetProviderMetrics":\n        return PROVIDER_ROUTER.metrics()\n\n'''
if cap.strip() not in s:
    s = s.replace(marker, cap + marker)
# Wrap chat result with structured contract at dispatch boundary for deterministic tool actions too.
needle = '        res = sarembok_process_dialogue(prompt, context=context if isinstance(context, list) else None, api_key=api_key, session_id=session_id)\n        res["agentId"] = "sarembok-prime"\n'
repl = '        res = sarembok_process_dialogue(prompt, context=context if isinstance(context, list) else None, api_key=api_key, session_id=session_id)\n        if "structuredResponse" not in res:\n            res["structuredResponse"] = build_structured_response(res.get("response", ""), action=res.get("action"), provider=res.get("source"), model=res.get("model"), latency_ms=res.get("metadata", {}).get("latency_ms") if isinstance(res.get("metadata"), dict) else None)\n        res["agentId"] = "sarembok-prime"\n'
s = s.replace(needle, repl)
SERVER.write_text(s, encoding='utf-8')

c = COMPOSE.read_text(encoding='utf-8')
if 'OPENROUTER_API_KEY:' not in c:
    c = c.replace('OPENAI_API_KEY: ${OPENAI_API_KEY:-}\n', 'OPENAI_API_KEY: ${OPENAI_API_KEY:-}\n      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}\n      GROQ_API_KEY: ${GROQ_API_KEY:-}\n')
if 'GEMINI_MODEL:' not in c:
    c = c.replace('GEMINI_API_KEY: ${GEMINI_API_KEY:-}\n', 'GEMINI_API_KEY: ${GEMINI_API_KEY:-}\n      GEMINI_MODEL: ${GEMINI_MODEL:-gemini-3.8-flash}\n      SAREMBOK_GEMINI_API: ${SAREMBOK_GEMINI_API:-interactions}\n      SAREMBOK_GEMINI_THINKING_LEVEL: ${SAREMBOK_GEMINI_THINKING_LEVEL:-low}\n      SAREMBOK_PROVIDER_ORDER: ${SAREMBOK_PROVIDER_ORDER:-Gemini,OpenRouter,Groq,OpenAI,Custom}\n')
if 'OPENROUTER_MODEL:' not in c:
    c = c.replace('LLM_MODEL: ${LLM_MODEL:-}\n', 'LLM_MODEL: ${LLM_MODEL:-}\n      OPENROUTER_MODEL: ${OPENROUTER_MODEL:-openai/gpt-oss-120b}\n      GROQ_MODEL: ${GROQ_MODEL:-openai/gpt-oss-120b}\n      SAREMBOK_LLM_MAX_OUTPUT_TOKENS: ${SAREMBOK_LLM_MAX_OUTPUT_TOKENS:-800}\n')
COMPOSE.write_text(c, encoding='utf-8')

# Add local contract tests without needing credentials.
test = ROOT/'Deployment/cloud/test_phase2_6.py'
write(test, '''import os, sys, tempfile\nsys.path.insert(0, os.path.dirname(__file__))\nfrom provider_router import ProviderRouter\nfrom capability_registry import CapabilityRegistry\nfrom structured_response import build_structured_response\n\ndef test_capabilities():\n    s=CapabilityRegistry().snapshot({"onlineWorkers":0})\n    assert any(x["method"]=="SarembokChat" for x in s["capabilities"])\n    assert all("enabled" in x for x in s["capabilities"])\n\ndef test_structured():\n    r=build_structured_response("# Hello\\n\\nAnswer.", provider="Gemini", model="gemini-3.8-flash", latency_ms=123.4)\n    assert r["type"]=="response" and r["speaker"]=="sarembok"\n    assert r["metadata"]["latency_ms"]==123.4\n\ndef test_provider_config_empty_is_truthful(monkeypatch):\n    for k in ["OPENAI_API_KEY","OPENROUTER_API_KEY","GROQ_API_KEY","GEMINI_API_KEY","LLM_ENDPOINT_URL"]: monkeypatch.delenv(k, raising=False)\n    assert ProviderRouter().configured()==[]\n''')
PY
