# Sarembok VE Operations & Maintenance Guide

## Database Management & Backup

The SQLite database file is located at `/data/sarembok_cloud.db` inside the container (backed by Docker volume `sarembok-data`).

### Creating a Hot Backup
Because SQLite is configured in WAL mode (`PRAGMA journal_mode=WAL`), backups can be created safely while the runtime is running:

```bash
docker exec sarembok-runtime sqlite3 /data/sarembok_cloud.db ".backup /data/backup_sarembok.db"
```

### Restoring Database Backup
To restore from backup:
```bash
docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml stop sarembok-runtime
docker run --rm -v sarembok-data:/data alpine cp /data/backup_sarembok.db /data/sarembok_cloud.db
docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml start sarembok-runtime
```

---

## Log Inspection & Diagnostics

### View Live Container Logs
```bash
docker logs -f --tail=100 sarembok-runtime
docker logs -f --tail=100 sarembok-edge
```

### Inspect Container Health
```bash
docker inspect --format='{{json .State.Health}}' sarembok-runtime
```
