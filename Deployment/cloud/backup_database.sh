#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
BACKUP_DIR="$ROOT/Deployment/cloud/backups"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CONTAINER_TMP="/data/.sarembok_cloud_backup_${STAMP}.db"
HOST_BACKUP="$BACKUP_DIR/sarembok_cloud_${STAMP}.db"

cleanup() {
    docker exec sarembok-runtime rm -f "$CONTAINER_TMP" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Creating consistent SQLite backup..."
docker exec sarembok-runtime python -c '
import os
import sqlite3
import sys

src = "/data/sarembok_cloud.db"
dst = sys.argv[1]

if not os.path.isfile(src):
    raise SystemExit(f"source database missing: {src}")

try:
    os.unlink(dst)
except FileNotFoundError:
    pass

with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
    s.backup(d)
    result = d.execute("PRAGMA integrity_check").fetchone()[0]
    if str(result).lower() != "ok":
        raise SystemExit(f"integrity_check failed: {result}")

size = os.path.getsize(dst)
if size <= 0:
    raise SystemExit("backup database is empty")

print(f"SQLite backup integrity: ok ({size} bytes)")
' "$CONTAINER_TMP"

docker exec sarembok-runtime test -s "$CONTAINER_TMP"
docker cp "sarembok-runtime:${CONTAINER_TMP}" "$HOST_BACKUP"
test -s "$HOST_BACKUP"

sha256sum "$HOST_BACKUP" > "${HOST_BACKUP}.sha256"
chmod 600 "$HOST_BACKUP" "${HOST_BACKUP}.sha256"
printf 'Verified backup: %s\n' "$HOST_BACKUP"
printf 'Checksum: %s\n' "${HOST_BACKUP}.sha256"
