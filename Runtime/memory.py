import sqlite3
from datetime import datetime


class SarembokMemory:
    def __init__(self, database="sarembok_memory.db"):
        self.db = sqlite3.connect(database)
        self._init_db()

    def _init_db(self):
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY,
            key TEXT,
            value TEXT,
            created TEXT
        )
        """)
        self.db.commit()

    def remember(self, key, value):
        self.db.execute(
            "INSERT INTO memories(key,value,created) VALUES(?,?,?)",
            (key, value, datetime.utcnow().isoformat())
        )
        self.db.commit()

    def recall(self, key):
        row = self.db.execute(
            "SELECT value FROM memories WHERE key=? ORDER BY id DESC LIMIT 1",
            (key,)
        ).fetchone()
        return row[0] if row else None
