"""Sarembok Event-Driven Architecture & Pub/Sub Bus.

Provides decoupled asynchronous messaging, topic routing, CloudEvents v1.0 compliance,
consumer groups, and optional Apache Kafka / Redpanda broker bridging.
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from sarembok_distributed_tracing import tracer, Span

LOG = logging.getLogger("sarembok.event_bus")


class CloudEvent:
    """CloudEvents v1.0 specification compliant event."""

    def __init__(
        self,
        event_type: str,
        source: str,
        data: Any,
        event_id: Optional[str] = None,
        subject: Optional[str] = None,
        traceparent: Optional[str] = None,
        datacontenttype: str = "application/json",
    ) -> None:
        self.id = event_id or f"evt_{secrets.token_hex(12)}"
        self.source = source
        self.specversion = "1.0"
        self.type = event_type
        self.time = datetime.now(timezone.utc).isoformat()
        self.subject = subject
        self.data = data
        self.datacontenttype = datacontenttype
        self.traceparent = traceparent or (tracer.current_span().to_w3c_traceparent() if tracer.current_span() else None)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "specversion": self.specversion,
            "id": self.id,
            "source": self.source,
            "type": self.type,
            "time": self.time,
            "datacontenttype": self.datacontenttype,
            "data": self.data,
        }
        if self.subject:
            payload["subject"] = self.subject
        if self.traceparent:
            payload["traceparent"] = self.traceparent
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CloudEvent:
        return cls(
            event_type=data.get("type", "unknown"),
            source=data.get("source", "sarembok"),
            data=data.get("data"),
            event_id=data.get("id"),
            subject=data.get("subject"),
            traceparent=data.get("traceparent"),
            datacontenttype=data.get("datacontenttype", "application/json"),
        )


SubscriptionCallback = Callable[[CloudEvent], Coroutine[Any, Any, None]]


class EventBus:
    """Asynchronous topic-based event bus with Kafka bridge support."""

    def __init__(self, max_buffer_per_topic: int = 1000) -> None:
        self.max_buffer_per_topic = max_buffer_per_topic
        self._subscribers: Dict[str, Set[SubscriptionCallback]] = {}
        self._pattern_subscribers: Dict[str, Set[SubscriptionCallback]] = {}
        self._topic_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self._kafka_enabled = bool(os.getenv("KAFKA_BOOTSTRAP_SERVERS"))
        self._kafka_producer: Any = None
        self._lock = asyncio.Lock()

    def subscribe(self, topic_or_pattern: str, callback: SubscriptionCallback) -> None:
        """Subscribe an async handler to a topic or wildcard pattern (e.g. 'sarembok.cdc.*')."""
        if "*" in topic_or_pattern or "?" in topic_or_pattern:
            if topic_or_pattern not in self._pattern_subscribers:
                self._pattern_subscribers[topic_or_pattern] = set()
            self._pattern_subscribers[topic_or_pattern].add(callback)
        else:
            if topic_or_pattern not in self._subscribers:
                self._subscribers[topic_or_pattern] = set()
            self._subscribers[topic_or_pattern].add(callback)
        LOG.debug("Subscribed callback to %s", topic_or_pattern)

    def unsubscribe(self, topic_or_pattern: str, callback: SubscriptionCallback) -> None:
        if topic_or_pattern in self._subscribers:
            self._subscribers[topic_or_pattern].discard(callback)
        if topic_or_pattern in self._pattern_subscribers:
            self._pattern_subscribers[topic_or_pattern].discard(callback)

    async def publish(
        self,
        topic: str,
        event_or_data: Any,
        source: str = "sarembok.runtime",
        event_type: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> CloudEvent:
        """Publish a message to a topic and broadcast to all matching subscribers."""
        with tracer.start_span("event_bus.publish", attributes={"messaging.destination": topic, "messaging.system": "sarembok_bus"}) as span:
            if isinstance(event_or_data, CloudEvent):
                event = event_or_data
            else:
                event = CloudEvent(
                    event_type=event_type or f"{topic}.event",
                    source=source,
                    data=event_or_data,
                    subject=subject or topic,
                    traceparent=span.to_w3c_traceparent(),
                )

            span.set_attribute("messaging.message_id", event.id)

            # Store in internal topic replay buffer
            if topic not in self._topic_buffers:
                self._topic_buffers[topic] = []
            self._topic_buffers[topic].append(event.to_dict())
            if len(self._topic_buffers[topic]) > self.max_buffer_per_topic:
                self._topic_buffers[topic] = self._topic_buffers[topic][-self.max_buffer_per_topic :]

            # Find all matching callbacks
            callbacks: Set[SubscriptionCallback] = set()
            if topic in self._subscribers:
                callbacks.update(self._subscribers[topic])

            for pattern, cbs in self._pattern_subscribers.items():
                if fnmatch.fnmatch(topic, pattern):
                    callbacks.update(cbs)

            # Asynchronously dispatch to local subscribers
            dispatch_tasks = []
            for cb in callbacks:
                dispatch_tasks.append(self._safe_dispatch(cb, event, topic))

            if dispatch_tasks:
                await asyncio.gather(*dispatch_tasks, return_exceptions=True)

            # Optional Kafka dispatch if configured
            if self._kafka_enabled:
                await self._forward_to_kafka(topic, event)

            return event

    async def _safe_dispatch(self, cb: SubscriptionCallback, event: CloudEvent, topic: str) -> None:
        try:
            with tracer.start_span(f"event_bus.consume", traceparent=event.traceparent, attributes={"messaging.destination": topic, "messaging.message_id": event.id}):
                await cb(event)
        except Exception as err:
            LOG.error("Error in event subscriber for topic %s: %s", topic, err, exc_info=True)

    async def _forward_to_kafka(self, topic: str, event: CloudEvent) -> None:
        """Optional Kafka connector forwarding message to external Kafka/Redpanda cluster."""
        servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        if not servers:
            return
        try:
            # Dynamically use aiokafka or confluent_kafka if installed
            import aiokafka  # type: ignore
            if not self._kafka_producer:
                self._kafka_producer = aiokafka.AIOKafkaProducer(bootstrap_servers=servers)
                await self._kafka_producer.start()
            await self._kafka_producer.send_and_wait(
                topic=topic.replace(".", "_"),
                value=json.dumps(event.to_dict()).encode("utf-8"),
                headers=[("traceparent", (event.traceparent or "").encode("utf-8"))],
            )
        except ImportError:
            # Fallback mock/log when aiokafka is not installed
            LOG.info("[KAFKA_BRIDGE] Kafka servers configured (%s) but aiokafka not installed; routed via local bus", servers)
        except Exception as e:
            LOG.warning("[KAFKA_BRIDGE] Failed forwarding to external Kafka: %s", e)

    def get_topic_events(self, topic: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent events from topic replay buffer."""
        return list(self._topic_buffers.get(topic, []))[-limit:]

    def clear(self) -> None:
        self._subscribers.clear()
        self._pattern_subscribers.clear()
        self._topic_buffers.clear()


# Global singleton event bus
event_bus = EventBus()
