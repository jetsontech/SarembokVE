"""Sarembok Distributed Tracing Engine (OpenTelemetry W3C TraceContext compliant).

Provides full observability across RPC calls, agent reasoning, event bus pub/sub,
and Change Data Capture (CDC) pipelines.
"""

from __future__ import annotations

import contextvars
import os
import re
import secrets
import threading
import time
from typing import Any, Dict, List, Optional


# W3C TraceContext regex: 00-{32 hex trace_id}-{16 hex parent_id}-{2 hex flags}
_TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")

_current_span_var: contextvars.ContextVar[Optional[Span]] = contextvars.ContextVar(
    "sarembok_current_span", default=None
)


def generate_trace_id() -> str:
    """Generate a random 128-bit trace ID formatted as a 32-character hex string."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Generate a random 64-bit span ID formatted as a 16-character hex string."""
    return secrets.token_hex(8)


class Span:
    """Represents a single operation in a distributed trace."""

    def __init__(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.trace_id = trace_id or generate_trace_id()
        self.span_id = generate_span_id()
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.status = "OK"
        self.error_message: Optional[str] = None
        self.attributes: Dict[str, Any] = dict(attributes or {})
        self.events: List[Dict[str, Any]] = []
        self._prev_token: Any = None

    def set_attribute(self, key: str, value: Any) -> Span:
        self.attributes[str(key)] = value
        return self

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Span:
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": dict(attributes or {})
        })
        return self

    def set_error(self, message: str) -> Span:
        self.status = "ERROR"
        self.error_message = str(message)
        self.set_attribute("error", True)
        self.set_attribute("error.message", str(message))
        return self

    def finish(self, status: Optional[str] = None) -> Span:
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = round((self.end_time - self.start_time) * 1000, 3)
        if status:
            self.status = status
        tracer.record_span(self)
        return self

    def to_w3c_traceparent(self) -> str:
        """Format as W3C traceparent header: 00-{trace_id}-{span_id}-01."""
        return f"00-{self.trace_id}-{self.span_id}-01"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "attributes": self.attributes,
            "events": self.events,
            "traceparent": self.to_w3c_traceparent(),
        }

    def __enter__(self) -> Span:
        self._prev_token = _current_span_var.set(self)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_val is not None:
            self.set_error(str(exc_val))
        self.finish()
        if self._prev_token is not None:
            _current_span_var.reset(self._prev_token)

    async def __aenter__(self) -> Span:
        self._prev_token = _current_span_var.set(self)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_val is not None:
            self.set_error(str(exc_val))
        self.finish()
        if self._prev_token is not None:
            _current_span_var.reset(self._prev_token)


class Tracer:
    """Manages spans, context propagation, and trace buffer storage."""

    def __init__(self, max_retained_spans: int = 5000) -> None:
        self.max_retained_spans = max_retained_spans
        self._spans: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def current_span(self) -> Optional[Span]:
        return _current_span_var.get()

    def start_span(
        self,
        name: str,
        parent: Optional[Span] = None,
        traceparent: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        trace_id = None
        parent_span_id = None

        if parent is not None:
            trace_id = parent.trace_id
            parent_span_id = parent.span_id
        elif traceparent:
            parsed = self.parse_traceparent(traceparent)
            if parsed:
                trace_id, parent_span_id = parsed
        else:
            active = self.current_span()
            if active is not None:
                trace_id = active.trace_id
                parent_span_id = active.span_id

        return Span(
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            attributes=attributes,
        )

    def parse_traceparent(self, header_value: str) -> Optional[tuple[str, str]]:
        if not header_value:
            return None
        match = _TRACEPARENT_RE.match(header_value.strip().lower())
        if match:
            return (match.group(1), match.group(2))
        return None

    def inject_headers(self, headers: Dict[str, str], span: Optional[Span] = None) -> Dict[str, str]:
        target = span or self.current_span()
        if target:
            headers["traceparent"] = target.to_w3c_traceparent()
        return headers

    def extract_headers(self, headers: Dict[str, str], span_name: str = "operation") -> Span:
        raw_tp = headers.get("traceparent") or headers.get("Traceparent") or ""
        return self.start_span(name=span_name, traceparent=raw_tp)

    def record_span(self, span: Span) -> None:
        with self._lock:
            self._spans.append(span.to_dict())
            if len(self._spans) > self.max_retained_spans:
                self._spans = self._spans[-self.max_retained_spans :]

    def get_traces(
        self,
        limit: int = 50,
        trace_id: Optional[str] = None,
        name_filter: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            results = list(self._spans)

        if trace_id:
            results = [s for s in results if s.get("trace_id") == trace_id]
        if name_filter:
            results = [s for s in results if name_filter.lower() in s.get("name", "").lower()]
        if status:
            results = [s for s in results if s.get("status") == status]

        return results[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()


# Global singleton tracer
tracer = Tracer()
