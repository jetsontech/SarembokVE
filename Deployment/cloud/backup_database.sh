#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
BACKUP_DIR="$ROOT/Deployment/cloud/backups"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CONTAINER_TMP="/tmp/sarembok-${STAMP}.db"
HOST_BACKUP="$BACKUP_DIR/sarembok_cloud_${STAMP}.db"

echo "Creating consistent SQLite backup..."
docker exec sarembok-runtime python - "$CONTAINER_TMP" <<'PY'
import sqlite3, sys
src = "/data/sarembok_cloud.db"
dst = sys.argv[1]
with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
    s.backup(d)
    ok = d.execute("PRAGMA integrity_check").fetchone()[0]
    if ok != "ok":
        raise SystemExit(f"integrity_check failed: {ok}")
print("SQLite backup integrity: ok")
PY

docker cp "sarembok-runtime:${CONTAINER_TMP}" "$HOST_BACKUP"
docker exec sarembok-runtime rm -f "$CONTAINER_TMP"
sha256sum "$HOST_BACKUP" > "${HOST_BACKUP}.sha256"
chmod 600 "$HOST_BACKUP" "${HOST_BACKUP}.sha256"
printf 'Verified backup: %s\n' "$HOST_BACKUP"
printf 'Checksum: %s\n' "${HOST_BACKUP}.sha256"
