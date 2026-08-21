"""Sarembok VE conversation and model-provider runtime.

The cloud runtime owns agent identity, context assembly, persistent
conversation history, and memory. Model providers are interchangeable
adapters selected by environment configuration; no provider becomes part of
Sarembok's core architecture.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any


class ModelProviderError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelProvider:
    def __init__(self) -> None:
        self.provider = os.getenv("SAREMBOK_MODEL_PROVIDER", "openai").strip().lower()
        self.endpoint = os.getenv(
            "SAREMBOK_MODEL_ENDPOINT",
            "https://api.openai.com/v1/responses",
        ).strip()
        self.api_key = os.getenv("SAREMBOK_MODEL_API_KEY", "").strip()
        self.model = os.getenv("SAREMBOK_MODEL_NAME", "gpt-5.6-luna").strip()
        self.protocol = os.getenv("SAREMBOK_MODEL_PROTOCOL", "responses").strip().lower()
        self.timeout = max(5, int(os.getenv("SAREMBOK_MODEL_TIMEOUT", "90")))

    @property
    def configured(self) -> bool:
        if self.provider == "test":
            return True
        return bool(self.api_key) and self.provider not in {"", "disabled", "none"}

    def info(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "protocol": self.protocol,
            "configured": self.configured,
        }

    def complete(self, messages: list[dict[str, str]]) -> str:
        if self.provider == "test":
            return self._test_complete(messages)

        if not self.configured:
            raise ModelProviderError("model_provider_not_configured")
        if not self.endpoint:
            raise ModelProviderError("model_endpoint_not_configured")

        if self.protocol == "responses":
            payload = {"model": self.model, "input": messages}
        elif self.protocol in {"chat_completions", "chat-completions"}:
            payload = {"model": self.model, "messages": messages}
        else:
            raise ModelProviderError(f"unsupported_model_protocol: {self.protocol}")

        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "SarembokVE/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:2000]
            raise ModelProviderError(f"model_provider_http_{exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise ModelProviderError(f"model_provider_unreachable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ModelProviderError("model_provider_timeout") from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ModelProviderError("model_provider_invalid_json") from exc

        text = self._extract_text(data)
        if not text:
            raise ModelProviderError("model_provider_empty_response")
        return text.strip()

    @staticmethod
    def _test_complete(messages: list[dict[str, str]]) -> str:
        """Deterministic provider used for local/CI Sarembok validation.

        This provider never performs network I/O and never consumes external
        model quota. It exercises the same ConversationRuntime provider
        boundary used by production model adapters.
        """
        user_messages = [
            message.get("content", "").strip()
            for message in messages
            if message.get("role") == "user"
            and isinstance(message.get("content"), str)
        ]

        if not user_messages:
            return "Sarembok test provider is operational."

        return (
            "Sarembok test provider response: "
            + user_messages[-1]
        )

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                ]
                if parts:
                    return "".join(parts)

        output = data.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        parts.append(block["text"])
            if parts:
                return "".join(parts)

        return ""


class ConversationRuntime:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.provider = ModelProvider()
        self._init_schema()

    def _init_schema(self) -> None:
        self.store.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                session_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                provider TEXT,
                model TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conversation_agent_time
                ON conversation_messages(agent_id, created_at);
            CREATE TABLE IF NOT EXISTS agent_memories (
                memory_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                memory_type TEXT NOT NULL DEFAULT 'fact',
                content TEXT NOT NULL,
                importance REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_time
                ON agent_memories(agent_id, updated_at);
            """
        )
        self.store.db.commit()

    def provider_info(self) -> dict[str, Any]:
        return self.provider.info()

    def _history(self, agent_id: str, limit: int) -> list[dict[str, str]]:
        rows = self.store.db.execute(
            """
            SELECT role, content
            FROM conversation_messages
            WHERE agent_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (agent_id, limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def _memories(self, agent_id: str, limit: int) -> list[dict[str, Any]]:
        rows = self.store.db.execute(
            """
            SELECT memory_id, memory_type, content, importance, updated_at
            FROM agent_memories
            WHERE agent_id=?
            ORDER BY importance DESC, updated_at DESC
            LIMIT ?
            """,
            (agent_id, limit),
        ).fetchall()
        return [
            {
                "memoryId": r[0],
                "type": r[1],
                "content": r[2],
                "importance": r[3],
                "updatedAt": r[4],
            }
            for r in rows
        ]

    def remember(
        self,
        agent_id: str,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
    ) -> dict[str, Any]:
        content = content.strip()
        if not content:
            raise ValueError("memory content is required")
        importance = min(1.0, max(0.0, float(importance)))
        stamp = utc_now()
        memory_id = f"mem-{uuid.uuid4().hex[:12]}"
        self.store.db.execute(
            """
            INSERT INTO agent_memories(
                memory_id, agent_id, memory_type, content, importance, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (memory_id, agent_id, memory_type.strip() or "fact", content, importance, stamp, stamp),
        )
        self.store.db.commit()
        self.store.event(agent_id, "MEMORY_STORED", {"memoryId": memory_id, "type": memory_type})
        return {
            "memoryId": memory_id,
            "agentId": agent_id,
            "type": memory_type,
            "content": content,
            "importance": importance,
            "createdAt": stamp,
        }

    def recall(self, agent_id: str, limit: int = 20) -> dict[str, Any]:
        memories = self._memories(agent_id, min(100, max(1, int(limit))))
        return {"agentId": agent_id, "memories": memories, "count": len(memories)}

    def history(self, agent_id: str, limit: int = 50) -> dict[str, Any]:
        rows = self.store.db.execute(
            """
            SELECT message_id, session_id, role, content, provider, model, created_at
            FROM conversation_messages
            WHERE agent_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (agent_id, min(200, max(1, int(limit)))),
        ).fetchall()
        messages = [
            {
                "messageId": r[0],
                "sessionId": r[1],
                "role": r[2],
                "content": r[3],
                "provider": r[4],
                "model": r[5],
                "createdAt": r[6],
            }
            for r in reversed(rows)
        ]
        return {"agentId": agent_id, "messages": messages, "count": len(messages)}

    async def chat(
        self,
        agent_id: str,
        content: str,
        db_lock: asyncio.Lock,
        session_id: str | None = None,
        history_limit: int = 20,
        memory_limit: int = 10,
    ) -> dict[str, Any]:
        content = content.strip()
        if not content:
            raise ValueError("content is required")

        # Snapshot durable context while holding the same lock used by the
        # established runtime. The provider call happens after the lock is
        # released so one slow model request cannot block every RPC.
        async with db_lock:
            history = self._history(agent_id, min(50, max(0, int(history_limit))))
            memories = self._memories(agent_id, min(25, max(0, int(memory_limit))))

        memory_block = "\n".join(
            f"- [{item['type']}] {item['content']}"
            for item in memories
        ) or "(no persistent memories yet)"

        system = (
            "You are the conversational intelligence operating inside Sarembok VE. "
            "Sarembok VE owns agent identity, context, memory, orchestration, tools, "
            "and session state. You are a replaceable model provider, not Sarembok itself. "
            "Be truthful about what the platform has actually done.\n\n"
            "Persistent agent memory:\n"
            f"{memory_block}"
        )

        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": content})

        response_text = await asyncio.to_thread(self.provider.complete, messages)

        stamp = utc_now()
        user_id = f"msg-{uuid.uuid4().hex[:12]}"
        assistant_id = f"msg-{uuid.uuid4().hex[:12]}"
        provider = self.provider.provider
        model = self.provider.model

        async with db_lock:
            self.store.db.executemany(
                """
                INSERT INTO conversation_messages(
                    message_id, agent_id, session_id, role, content, provider, model, created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                [
                    (user_id, agent_id, session_id, "user", content, provider, model, stamp),
                    (assistant_id, agent_id, session_id, "assistant", response_text, provider, model, stamp),
                ],
            )
            self.store.db.commit()
            self.store.event(
                agent_id,
                "CHAT_COMPLETED",
                {
                    "userMessageId": user_id,
                    "assistantMessageId": assistant_id,
                    "provider": provider,
                    "model": model,
                    "memoryCount": len(memories),
                },
            )

        return {
            "agentId": agent_id,
            "sessionId": session_id,
            "userMessageId": user_id,
            "assistantMessageId": assistant_id,
            "content": response_text,
            "provider": provider,
            "model": model,
            "memoryCount": len(memories),
            "contextMessageCount": len(messages),
            "createdAt": stamp,
        }
