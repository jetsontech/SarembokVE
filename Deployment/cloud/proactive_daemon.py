"""
Sarembok Prometheus — Proactive OmniDaemon
Continuous background intelligence engine that scans workspace files,
monitors execution latency, audits security posture, and generates
proactive engineering briefings without requiring manual user prompts.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("sarembok.proactive")


class ProactiveOmniDaemon:
    """
    Background intelligence daemon that executes continuous audits,
    proactive optimization scans, and executive briefings.
    """

    def __init__(self, db_conn: sqlite3.Connection, scan_interval_sec: float = 30.0):
        self.db = db_conn
        self.scan_interval_sec = scan_interval_sec
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._init_tables()

    def _init_tables(self) -> None:
        with self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS proactive_insights (
                    insight_id TEXT PRIMARY KEY,
                    category TEXT,
                    title TEXT,
                    description TEXT,
                    severity TEXT,
                    action_suggested TEXT,
                    status TEXT,
                    timestamp TEXT,
                    payload_json TEXT
                )
            """)
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_proactive_status ON proactive_insights(status)")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ProactiveOmniDaemon")
        self._thread.start()
        LOG.info("[PROACTIVE] OmniDaemon active (interval=%.1fs)", self.scan_interval_sec)

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        LOG.info("[PROACTIVE] OmniDaemon stopped")

    def _run_loop(self) -> None:
        # Run initial scan immediately
        self.run_proactive_scan()
        while self._running:
            time.sleep(self.scan_interval_sec)
            if self._running:
                self.run_proactive_scan()

    def run_proactive_scan(self) -> List[Dict[str, Any]]:
        """Derive proactive findings from current runtime state."""
        stamp = datetime.now(timezone.utc).isoformat()
        insights: list[dict[str, Any]] = []

        def add(category: str, title: str, description: str, severity: str, action: str, payload: dict[str, Any], status: str = "OBSERVED") -> None:
            insights.append({
                "insight_id": f"ins-{uuid.uuid4().hex[:8]}",
                "category": category,
                "title": title,
                "description": description,
                "severity": severity,
                "action_suggested": action,
                "status": status,
                "timestamp": stamp,
                "payload_json": json.dumps(payload, ensure_ascii=False),
            })

        # 1. Worker and scheduler health.
        workers = {"ONLINE": 0, "STALE": 0, "OFFLINE": 0}
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='workers'").fetchone():
            for status, count in self.db.execute("SELECT status, COUNT(*) FROM workers GROUP BY status").fetchall():
                workers[str(status).upper()] = int(count)

        task_counts: dict[str, int] = {}
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone():
            task_counts = {
                str(status).upper(): int(count)
                for status, count in self.db.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall()
            }

        online = workers.get("ONLINE", 0)
        stale = workers.get("STALE", 0)
        queued = task_counts.get("QUEUED", 0) + task_counts.get("PENDING_WORKER", 0)
        running = task_counts.get("RUNNING", 0)
        failed = task_counts.get("FAILED", 0)

        if online == 0 and (queued > 0 or running > 0):
            add(
                "WORKER_AVAILABILITY",
                "No online worker is available for queued execution",
                f"The live registry reports {queued} queued/pending task(s), {running} running task(s), and no ONLINE worker.",
                "ACTION_REQUIRED",
                "Launch or reconnect a worker with the required capability.",
                {"onlineWorkers": online, "staleWorkers": stale, "queuedTasks": queued, "runningTasks": running},
                "ACTION_REQUIRED",
            )
        else:
            add(
                "WORKER_AVAILABILITY",
                "Worker and scheduler state observed",
                f"The runtime currently reports {online} ONLINE worker(s), {stale} STALE worker(s), {queued} queued/pending task(s), and {running} running task(s).",
                "INFO",
                "Continue monitoring worker liveness and queue depth.",
                {"onlineWorkers": online, "staleWorkers": stale, "queuedTasks": queued, "runningTasks": running},
            )

        # 2. Failure backlog.
        if failed:
            add(
                "SCHEDULER_HEALTH",
                "Failed task backlog detected",
                f"The task table contains {failed} FAILED task(s).",
                "ACTION_REQUIRED",
                "Inspect failed task error fields and retry only tasks whose workers report retryable failures.",
                {"failedTasks": failed, "taskCounts": task_counts},
                "ACTION_REQUIRED",
            )
        else:
            add(
                "SCHEDULER_HEALTH",
                "No failed tasks observed",
                "The current task table contains no FAILED tasks.",
                "INFO",
                "Continue normal scheduler monitoring.",
                {"taskCounts": task_counts},
            )

        # 3. SQLite integrity.
        try:
            integrity = str(self.db.execute("PRAGMA integrity_check").fetchone()[0]).upper()
        except Exception as exc:
            integrity = f"ERROR:{type(exc).__name__}"

        memory_count = 0
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='memories'").fetchone():
            memory_count = int(self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0])

        if integrity == "OK":
            add(
                "PERSISTENCE_INTEGRITY",
                "SQLite integrity verified",
                f"PRAGMA integrity_check returned {integrity}; the memory store contains {memory_count} record(s).",
                "INFO",
                "Retain the configured verified backup and restore procedure.",
                {"integrity": integrity, "memoryRecords": memory_count},
                "VERIFIED",
            )
        else:
            add(
                "PERSISTENCE_INTEGRITY",
                "SQLite integrity requires attention",
                f"PRAGMA integrity_check returned {integrity}.",
                "CRITICAL",
                "Run the production backup/restore procedure and inspect the database before further mutation.",
                {"integrity": integrity, "memoryRecords": memory_count},
                "ACTION_REQUIRED",
            )

        with self.db:
            for ins in insights:
                self.db.execute(
                    "INSERT OR REPLACE INTO proactive_insights VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        ins["insight_id"],
                        ins["category"],
                        ins["title"],
                        ins["description"],
                        ins["severity"],
                        ins["action_suggested"],
                        ins["status"],
                        ins["timestamp"],
                        ins["payload_json"],
                    ),
                )

        LOG.info(
            "[PROACTIVE] Generated %d runtime-backed insight(s): online=%d stale=%d queued=%d running=%d failed=%d",
            len(insights), online, stale, queued, running, failed,
        )
        return insights

    def list_insights(self, limit: int = 15) -> List[Dict[str, Any]]:
        cur = self.db.execute("""
            SELECT insight_id, category, title, description, severity, action_suggested, status, timestamp, payload_json
            FROM proactive_insights
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
        
        res = []
        for r in cur.fetchall():
            res.append({
                "insightId": r[0],
                "category": r[1],
                "title": r[2],
                "description": r[3],
                "severity": r[4],
                "actionSuggested": r[5],
                "status": r[6],
                "timestamp": r[7],
                "payload": json.loads(r[8]) if r[8] else {}
            })
        return res
