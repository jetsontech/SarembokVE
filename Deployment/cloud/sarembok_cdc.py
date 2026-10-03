"""Sarembok Change Data Capture (CDC) Pipeline.

Captures real-time table mutations and transaction logs, formats them into standard
Debezium/Kafka-compatible change event streams, and publishes them to the event bus.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import sqlite3
import time
from typing import Any, Dict, List, Optional

from sarembok_distributed_tracing import tracer
from sarembok_event_bus import event_bus, CloudEvent

LOG = logging.getLogger("sarembok.cdc")


class CDCOperation:
    CREATE = "c"
    UPDATE = "u"
    DELETE = "d"
    SNAPSHOT = "r"


class CDCRecord:
    """Standardized Change Data Capture mutation record."""

    def __init__(
        self,
        table: str,
        op: str,
        after: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        tx_id: Optional[str] = None,
        database: str = "sarembok_cloud",
    ) -> None:
        self.ts_ms = int(time.time() * 1000)
        self.tx_id = tx_id or f"tx_{secrets.token_hex(8)}"
        self.table = table
        self.op = op
        self.before = before
        self.after = after
        self.source = {
            "version": "1.0.0",
            "connector": "sarembok-cdc",
            "db": database,
            "table": table,
            "ts_ms": self.ts_ms,
            "tx_id": self.tx_id,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op": self.op,
            "ts_ms": self.ts_ms,
            "source": self.source,
            "before": self.before,
            "after": self.after,
        }


class CDCPipeline:
    """Manages real-time data streaming and mutation capture from persistent storage."""

    def __init__(self) -> None:
        self._mutation_log: List[Dict[str, Any]] = []
        self._max_log_size = 5000

    async def emit_change(
        self,
        table: str,
        op: str,
        after: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        tx_id: Optional[str] = None,
    ) -> CDCRecord:
        """Capture and emit a database row mutation onto the real-time event stream."""
        with tracer.start_span("cdc.capture", attributes={"db.table": table, "cdc.op": op}) as span:
            record = CDCRecord(table=table, op=op, after=after, before=before, tx_id=tx_id)
            span.set_attribute("cdc.tx_id", record.tx_id)

            record_dict = record.to_dict()
            self._mutation_log.append(record_dict)
            if len(self._mutation_log) > self._max_log_size:
                self._mutation_log = self._mutation_log[-self._max_log_size :]

            # Publish onto topic: sarembok.cdc.<table_name>
            topic = f"sarembok.cdc.{table}"
            await event_bus.publish(
                topic=topic,
                event_or_data=record_dict,
                source=f"sarembok.cdc.{table}",
                event_type=f"sarembok.cdc.{table}.{op}",
                subject=table,
            )

            # Automated Semantic Vector Indexing for text-bearing mutations
            if after and op in (CDCOperation.CREATE, CDCOperation.UPDATE):
                text_content = after.get("content") or after.get("prompt") or after.get("goal") or after.get("document") or after.get("text")
                if text_content and isinstance(text_content, str) and len(text_content.strip()) > 5:
                    try:
                        from sarembok_vector_store import vector_store
                        vector_store.insert(
                            collection=table,
                            record_id=f"cdc_{table}_{record.tx_id}",
                            document=text_content.strip(),
                            metadata={"cdc_table": table, "cdc_op": op, "cdc_tx": record.tx_id}
                        )
                    except Exception as err:
                        LOG.debug("Automatic CDC vector indexer notice: %s", err)

            LOG.debug("CDC emitted %s on %s (tx: %s)", op, table, record.tx_id)
            return record

    async def capture_insert(self, table: str, row: Dict[str, Any], tx_id: Optional[str] = None) -> CDCRecord:
        return await self.emit_change(table=table, op=CDCOperation.CREATE, after=row, before=None, tx_id=tx_id)

    async def capture_update(
        self,
        table: str,
        before: Dict[str, Any],
        after: Dict[str, Any],
        tx_id: Optional[str] = None,
    ) -> CDCRecord:
        return await self.emit_change(table=table, op=CDCOperation.UPDATE, after=after, before=before, tx_id=tx_id)

    async def capture_delete(self, table: str, before: Dict[str, Any], tx_id: Optional[str] = None) -> CDCRecord:
        return await self.emit_change(table=table, op=CDCOperation.DELETE, after=None, before=before, tx_id=tx_id)

    async def snapshot_table(self, db_conn: sqlite3.Connection, table: str, limit: int = 500) -> List[CDCRecord]:
        """Perform initial sync snapshot of an existing table."""
        with tracer.start_span("cdc.snapshot", attributes={"db.table": table}):
            cursor = db_conn.cursor()
            cursor.execute(f"SELECT * FROM {table} LIMIT {limit}")
            columns = [desc[0] for desc in cursor.description]
            records = []
            tx_id = f"snap_{secrets.token_hex(6)}"

            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                rec = await self.emit_change(
                    table=table,
                    op=CDCOperation.SNAPSHOT,
                    after=row_dict,
                    before=None,
                    tx_id=tx_id,
                )
                records.append(rec)
            return records

    def get_change_log(self, table: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if not table:
            return self._mutation_log[-limit:]
        filtered = [r for r in self._mutation_log if r.get("source", {}).get("table") == table]
        return filtered[-limit:]


# Global singleton CDC pipeline
cdc_pipeline = CDCPipeline()
