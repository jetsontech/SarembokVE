"""Sarembok provider routing, streaming, health, and latency telemetry."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any, Callable


TRANSIENT_HTTP = {408, 429, 500, 502, 503, 504}
_STREAM_CALLBACK: ContextVar[Callable[[str], None] | None] = ContextVar("sarembok_stream_callback", default=None)
logger = logging.getLogger("sarembok.provider_router")

# Shared process-level provider health. ProviderRouter instances may be created
# per request, so cooldown state must live outside the instance.
_PROVIDER_COOLDOWNS: dict[str, float] = {}


def set_stream_callback(callback: Callable[[str], None] | None):
    return _STREAM_CALLBACK.set(callback)


def reset_stream_callback(token) -> None:
    _STREAM_CALLBACK.reset(token)


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
    ttft_ms: float | None = None


class ProviderRouter:
    def __init__(self) -> None:
        self.provider_timeout = max(5, int(os.getenv('SAREMBOK_LLM_PROVIDER_TIMEOUT_SECONDS', '60')))
        self.total_timeout = max(5, int(os.getenv('SAREMBOK_LLM_TOTAL_TIMEOUT_SECONDS', '90')))
        self.gemini_api = os.getenv('SAREMBOK_GEMINI_API', 'interactions').strip().lower()
        self.gemini_thinking = os.getenv('SAREMBOK_GEMINI_THINKING_LEVEL', 'low').strip().lower()
        if self.gemini_thinking not in {'low', 'medium', 'high'}:
            self.gemini_thinking = 'low'
        self.openrouter_reasoning = os.getenv('SAREMBOK_OPENROUTER_REASONING_EFFORT', 'low').strip().lower()
        if self.openrouter_reasoning not in {'minimal', 'low', 'medium', 'high', 'xhigh'}:
            self.openrouter_reasoning = 'low'
        self.max_output_tokens = max(64, int(os.getenv('SAREMBOK_LLM_MAX_OUTPUT_TOKENS', '8192')))
        self._history: deque[dict[str, Any]] = deque(maxlen=200)

    @staticmethod
    def _provider_available(name: str) -> bool:
        until = _PROVIDER_COOLDOWNS.get(name, 0.0)
        if until <= time.monotonic():
            _PROVIDER_COOLDOWNS.pop(name, None)
            return True
        return False

    @staticmethod
    def _set_provider_cooldown(name: str, seconds: float) -> None:
        _PROVIDER_COOLDOWNS[name] = time.monotonic() + seconds

    @staticmethod
    def _http_error_body(exc: urllib.error.HTTPError) -> str:
        try:
            raw = exc.read()
            return raw.decode('utf-8', errors='replace')
        except Exception:
            return ''

    @staticmethod
    def _classify_http_error(body: str) -> str:
        lowered = body.lower()
        if any(marker in lowered for marker in ('quota exceeded', 'free_tier', 'quota')):
            return 'quota_exceeded'
        if 'rate limit' in lowered or 'too many requests' in lowered:
            return 'rate_limited'
        return 'http_error'

    @staticmethod
    def _finish_reason(payload: dict[str, Any]) -> str | None:
        try:
            return payload['choices'][0].get('finish_reason')
        except (KeyError, IndexError, AttributeError, TypeError):
            return None

    @staticmethod
    def _extract_openai(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        choices = payload.get('choices') or []
        if not choices:
            raise RuntimeError('provider returned no choices')
        message = choices[0].get('message') or {}
        content = message.get('content')
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'text' and item.get('text'):
                    parts.append(str(item['text']))
            content = ''.join(parts)
        text = str(content).strip() if content else ''
        if not text:
            finish_reason = choices[0].get('finish_reason')
            raise RuntimeError(f"provider returned empty assistant content; finish_reason={finish_reason}")
        usage = payload.get('usage', {}) or {}
        finish_reason = choices[0].get('finish_reason')
        if finish_reason:
            usage = dict(usage)
            usage['_finish_reason'] = finish_reason
        return text, usage

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
            for cand in payload.get('candidates', []) or []:
                for part in cand.get('content', {}).get('parts', []) or []:
                    if part.get('text'):
                        parts.append(part['text'])
        if not parts:
            raise RuntimeError('Gemini returned no model output')
        return ''.join(parts).strip(), payload.get('usage', {}) or {}

    @staticmethod
    def _sse_events(response) -> Any:
        event_name = None
        data_lines: list[str] = []
        for raw_line in response:
            line = raw_line.decode('utf-8', errors='replace').rstrip('\r\n')
            if line.startswith('event:'):
                event_name = line[6:].strip()
            elif line.startswith('data:'):
                data_lines.append(line[5:].lstrip())
            elif not line:
                if data_lines:
                    raw_data = '\n'.join(data_lines)
                    if raw_data == '[DONE]':
                        yield event_name or 'done', None
                    else:
                        try:
                            yield event_name or 'message', json.loads(raw_data)
                        except json.JSONDecodeError:
                            pass
                event_name = None
                data_lines = []
        if data_lines:
            raw_data = '\n'.join(data_lines)
            if raw_data != '[DONE]':
                try:
                    yield event_name or 'message', json.loads(raw_data)
                except json.JSONDecodeError:
                    pass

    def _openai_headers(self, spec: ProviderSpec, streaming: bool = False) -> dict[str, str]:
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {spec.key}'}
        if streaming:
            headers['Accept'] = 'text/event-stream'
        if spec.name == 'OpenRouter':
            headers.update({'HTTP-Referer': 'https://sarembok.com', 'X-Title': 'Sarembok VE'})
        return headers

    def _openai_payload(self, spec: ProviderSpec, messages: list[dict[str, str]], streaming: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            'model': spec.model,
            'messages': messages,
            'max_tokens': self.max_output_tokens,
            'temperature': 0.7,
        }
        if streaming:
            data['stream'] = True
        if spec.name == 'OpenRouter':
            # gpt-oss-120b is a reasoning model. Keep reasoning internal and
            # bound its effort so interactive Sarembok requests reach visible
            # assistant content promptly. OpenRouter documents reasoning.effort
            # for this model; reasoning is never forwarded to the client.
            data['reasoning'] = {
                'effort': self.openrouter_reasoning,
                'exclude': True,
            }
        return data

    def _handle_http_error(self, spec: ProviderSpec, exc: urllib.error.HTTPError, attempts: int, deadline: float) -> None:
        body = self._http_error_body(exc)
        classification = self._classify_http_error(body)
        if exc.code == 429:
            cooldown = 300.0 if classification == 'quota_exceeded' else 30.0
            self._set_provider_cooldown(spec.name, cooldown)
            raise RuntimeError(f'{spec.name} {classification}; provider cooldown={int(cooldown)}s')
        if exc.code not in TRANSIENT_HTTP or attempts >= 2:
            detail = body[:500].replace('\n', ' ')
            raise RuntimeError(f'{spec.name} HTTP {exc.code}: {detail}')
        delay = min(1.5, 0.35 * (2 ** (attempts - 1)))
        if deadline - time.monotonic() <= delay + 1:
            raise TimeoutError(f'{spec.name} transient HTTP {exc.code}; deadline exceeded')
        time.sleep(delay)

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
            data = self._openai_payload(spec, messages)
            headers = self._openai_headers(spec)
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
                    text, usage = self._extract_openai(payload)
                return text, usage, api_name
            except urllib.error.HTTPError as exc:
                self._handle_http_error(spec, exc, attempts, deadline)

    def _request_stream(self, spec: ProviderSpec, system_prompt: str, prompt: str, messages: list[dict[str, str]], deadline: float, on_delta: Callable[[str], None]) -> tuple[str, dict[str, Any], str, float]:
        if spec.kind == 'gemini' and self.gemini_api == 'interactions':
            data = {
                'model': spec.model,
                'system_instruction': system_prompt,
                'input': prompt,
                'store': False,
                'stream': True,
                'generation_config': {
                    'thinking_level': self.gemini_thinking,
                    'max_output_tokens': self.max_output_tokens,
                },
            }
            headers = {'Content-Type': 'application/json', 'Accept': 'text/event-stream', 'x-goog-api-key': spec.key}
        elif spec.kind == 'openai':
            data = self._openai_payload(spec, messages, streaming=True)
            headers = self._openai_headers(spec, streaming=True)
        else:
            raise RuntimeError('streaming is unsupported for this provider')

        req = urllib.request.Request(spec.endpoint, data=json.dumps(data).encode('utf-8'), headers=headers)
        attempts = 0
        while True:
            attempts += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('provider deadline exceeded')
            timeout = min(self.provider_timeout, max(1, remaining))
            started = time.monotonic()
            try:
                text_parts: list[str] = []
                usage: dict[str, Any] = {}
                ttft_ms: float | None = None
                finish_reason: str | None = None
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    for event_name, event in self._sse_events(response):
                        if event_name == 'done' or event is None:
                            continue
                        if not isinstance(event, dict):
                            continue
                        if spec.kind == 'gemini':
                            if event_name == 'step.delta' or event.get('event_type') == 'step.delta':
                                delta = event.get('delta') or {}
                                if delta.get('type') == 'text' and delta.get('text'):
                                    chunk = str(delta['text'])
                                    if ttft_ms is None:
                                        ttft_ms = round((time.monotonic() - started) * 1000, 1)
                                    text_parts.append(chunk)
                                    on_delta(chunk)
                            elif event_name == 'interaction.completed' or event.get('event_type') == 'interaction.completed':
                                interaction = event.get('interaction') or {}
                                usage = interaction.get('usage') or event.get('usage') or {}
                        else:
                            choices = event.get('choices') or []
                            if choices:
                                choice = choices[0] or {}
                                finish_reason = choice.get('finish_reason') or finish_reason
                                delta = choice.get('delta') or {}
                                content = delta.get('content')
                                if isinstance(content, list):
                                    content = ''.join(str(x.get('text', '')) for x in content if isinstance(x, dict) and x.get('type') == 'text')
                                if content:
                                    chunk = str(content)
                                    if ttft_ms is None:
                                        ttft_ms = round((time.monotonic() - started) * 1000, 1)
                                    text_parts.append(chunk)
                                    on_delta(chunk)
                            if event.get('usage'):
                                usage = event.get('usage') or usage
                if not text_parts:
                    raise RuntimeError(f'{spec.name} stream returned no assistant content; finish_reason={finish_reason}')
                usage = dict(usage)
                if finish_reason:
                    usage['_finish_reason'] = finish_reason
                return ''.join(text_parts).strip(), usage, 'interactions' if spec.kind == 'gemini' else 'chat.completions.stream', ttft_ms or round((time.monotonic() - started) * 1000, 1)
            except urllib.error.HTTPError as exc:
                self._handle_http_error(spec, exc, attempts, deadline)

    def generate_stream(self, system_prompt: str, prompt: str, messages: list[dict[str, str]], on_delta: Callable[[str], None]) -> ProviderResult:
        providers = self.configured()
        if not providers:
            raise RuntimeError('no language-model provider configured')
        deadline = time.monotonic() + self.total_timeout
        failures: list[str] = []
        for spec in providers:
            if not self._provider_available(spec.name):
                logger.info('provider_skipped provider=%s model=%s reason=cooldown', spec.name, spec.model)
                failures.append(f'{spec.name}:cooldown')
                continue
            started = time.monotonic()
            try:
                if (spec.kind == 'gemini' and self.gemini_api == 'interactions') or spec.kind == 'openai':
                    text, usage, api_name, ttft_ms = self._request_stream(spec, system_prompt, prompt, messages, deadline, on_delta)
                else:
                    text, usage, api_name = self._request(spec, system_prompt, prompt, messages, deadline)
                    ttft_ms = round((time.monotonic() - started) * 1000, 1)
                    on_delta(text)
                latency_ms = round((time.monotonic() - started) * 1000, 1)
                record = {'provider': spec.name, 'model': spec.model, 'latency_ms': latency_ms, 'ttft_ms': ttft_ms, 'attempts': 1, 'api': api_name, 'ok': True, 'timestamp': time.time()}
                self._history.append(record)
                logger.info('provider_success provider=%s model=%s latency_ms=%s ttft_ms=%s api=%s finish_reason=%s', spec.name, spec.model, latency_ms, ttft_ms, api_name, usage.get('_finish_reason'))
                return ProviderResult(text, spec.name, spec.model, latency_ms, 1, api_name, usage, ttft_ms)
            except Exception as exc:
                latency_ms = round((time.monotonic() - started) * 1000, 1)
                error_message = str(exc)
                failures.append(f'{spec.name}:{type(exc).__name__}')
                self._history.append({'provider': spec.name, 'model': spec.model, 'latency_ms': latency_ms, 'attempts': 1, 'api': self.gemini_api if spec.kind == 'gemini' else 'chat.completions', 'ok': False, 'error': type(exc).__name__, 'error_message': error_message, 'timestamp': time.time()})
                logger.warning('provider_failed provider=%s model=%s error_type=%s error=%s', spec.name, spec.model, type(exc).__name__, error_message)
        raise RuntimeError('all providers failed: ' + ','.join(failures))

    def generate(self, system_prompt: str, prompt: str, messages: list[dict[str, str]]) -> ProviderResult:
        callback = _STREAM_CALLBACK.get()
        if callback is not None:
            return self.generate_stream(system_prompt, prompt, messages, callback)
        providers = self.configured()
        if not providers:
            raise RuntimeError('no language-model provider configured')
        deadline = time.monotonic() + self.total_timeout
        failures: list[str] = []
        for spec in providers:
            if not self._provider_available(spec.name):
                logger.info('provider_skipped provider=%s model=%s reason=cooldown', spec.name, spec.model)
                failures.append(f'{spec.name}:cooldown')
                continue
            started = time.monotonic()
            try:
                text, usage, api_name = self._request(spec, system_prompt, prompt, messages, deadline)
                latency_ms = round((time.monotonic() - started) * 1000, 1)
                self._history.append({'provider': spec.name, 'model': spec.model, 'latency_ms': latency_ms, 'attempts': 1, 'api': api_name, 'ok': True, 'timestamp': time.time()})
                logger.info('provider_success provider=%s model=%s latency_ms=%s api=%s finish_reason=%s', spec.name, spec.model, latency_ms, api_name, usage.get('_finish_reason'))
                return ProviderResult(text, spec.name, spec.model, latency_ms, 1, api_name, usage)
            except Exception as exc:
                latency_ms = round((time.monotonic() - started) * 1000, 1)
                error_message = str(exc)
                failures.append(f'{spec.name}:{type(exc).__name__}')
                self._history.append({'provider': spec.name, 'model': spec.model, 'latency_ms': latency_ms, 'attempts': 1, 'api': self.gemini_api if spec.kind == 'gemini' else 'chat.completions', 'ok': False, 'error': type(exc).__name__, 'error_message': error_message, 'timestamp': time.time()})
                logger.warning('provider_failed provider=%s model=%s error_type=%s error=%s', spec.name, spec.model, type(exc).__name__, error_message)
        raise RuntimeError('all providers failed: ' + ','.join(failures))

    def metrics(self) -> dict[str, Any]:
        entries = list(self._history)
        ok = [e for e in entries if e.get('ok')]
        cooldowns = {name: max(0, round(until - time.monotonic(), 1)) for name, until in _PROVIDER_COOLDOWNS.items() if until > time.monotonic()}
        return {'configuredProviders': [{'name': p.name, 'model': p.model, 'api': self.gemini_api if p.kind == 'gemini' else 'chat.completions'} for p in self.configured()], 'samples': len(entries), 'successes': len(ok), 'failures': len(entries) - len(ok), 'cooldowns': cooldowns, 'recent': entries[-20:]}
