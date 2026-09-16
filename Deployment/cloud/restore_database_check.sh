#!/usr/bin/env bash
set -Eeuo pipefail
BACKUP="${1:-}"
[ -n "$BACKUP" ] || { echo "Usage: $0 /path/to/backup.db"; exit 2; }
[ -f "$BACKUP" ] || { echo "ERROR: backup not found: $BACKUP"; exit 2; }

if command -v sha256sum >/dev/null 2>&1 && [ -f "${BACKUP}.sha256" ]; then
  sha256sum -c "${BACKUP}.sha256"
fi

python3 - "$BACKUP" <<'PY'
import sqlite3, sys
path = sys.argv[1]
with sqlite3.connect(path) as db:
    result = db.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise SystemExit(f"FAIL: SQLite integrity_check={result}")
    print("PASS: SQLite restore integrity_check=ok")
PY
