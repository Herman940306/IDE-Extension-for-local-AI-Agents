# AuraIA Disaster Recovery Runbook

**Last Updated:** 2025-10-19  
**Owners:** Platform Engineering (AuraIA)  
**Purpose:** Deliver repeatable backup and restoration procedures for the AuraIA backend data stores (Redis cache and Chroma vector database) and lay out the operational checks that must follow a disruptive incident.

---

## 1. Recovery Objectives

- **Recovery Time Objective (RTO):** < 60 minutes for cache-only loss; < 4 hours for full data store rehydration.
- **Recovery Point Objective (RPO):** 15 minutes for Redis (AOF + frequent snapshots); 1 hour for Chroma (volume snapshots).

---

## 2. Data Inventory

| System | Purpose | Persistence | Critical Data |
|--------|---------|-------------|----------------|
| Redis  | Session memory, rate limiting counters | Managed cache or containerised Redis 7 (AOF enabled) | `dump.rdb`, `appendonly.aof` |
| Chroma | Vector embeddings for semantic search | Backend volume `/var/lib/auraia/chroma` | Collection folders, `chroma.sqlite3` |

---

## 3. Backup Strategy

### 3.1 Redis

1. **Enable Append-Only File (AOF):** ensure `appendonly yes` and `appendfsync everysec` in `redis.conf` (already set in Docker Compose).
2. **Snapshot Policy:** configure `save 900 1` and `save 60 1000` to persist RDB snapshots on write thresholds.
3. **Offsite Copy:** run every 15 minutes on the host:
    ```bash
    */15 * * * * root /usr/bin/rsync -az /var/lib/redis/ s3://auraia-backups/redis/$(date +\%Y/\%m/\%d/\%H\%M)/
    ```
    Adjust for Azure Blob or other storage; apply 30-day retention + Glacier/archive after 7 days.
4. **Managed Redis:** enable point-in-time restore (PITR) or daily snapshots with 15-minute granularity when using Azure Cache or AWS ElastiCache.

### 3.2 Chroma

1. **Volume Layout:** backend container mounts `backend_chroma_data` at `/var/lib/auraia/chroma`.
2. **Snapshot Script (hourly):**
    ```bash
    #!/usr/bin/env bash
    set -euo pipefail
    TIMESTAMP=$(date +"%Y%m%d%H%M")
    SRC=/var/lib/auraia/chroma
    DEST=/mnt/backups/chroma
    mkdir -p "$DEST/$TIMESTAMP"
    rsync -a --delete "$SRC/" "$DEST/$TIMESTAMP/"
    tar -czf "$DEST/chroma-$TIMESTAMP.tgz" -C "$DEST/$TIMESTAMP" .
    az storage blob upload --account-name auraiaops --container-name chroma \
      --file "$DEST/chroma-$TIMESTAMP.tgz" --name "chroma-$TIMESTAMP.tgz"
    find "$DEST" -name 'chroma-*.tgz' -mtime +30 -delete
    ```
    Swap `az storage` for `aws s3` or `gcloud storage` per environment.
3. **Optional Quiesce:** call `/api/admin/maintenance/pause-indexing` before snapshotting when write volume is high; resume afterwards.

---

## 4. Recovery Procedures

### 4.1 Redis (Containerised)

1. Stop services:
    ```bash
    docker compose stop backend redis
    ```
2. Restore backup files into the named volume:
    ```bash
    docker run --rm \
      -v backend_redis_data:/data \
      -v /backups/redis/2025/10/19/1215:/restore \
      alpine sh -c 'cp /restore/dump.rdb /data/ && cp /restore/appendonly.aof /data/'
    ```
3. Start containers:
    ```bash
    docker compose up -d redis backend
    ```
4. Validate with `redis-cli --stat` and ensure backend `/health` returns `healthy: true`.

### 4.2 Redis (Managed Service)

1. Initiate PITR/snapshot restore through the provider portal.
2. Update `DB_REDIS_URL` secret if failover endpoint changes.
3. Redeploy backend to consume the restored endpoint.
4. Watch Prometheus for rate limit counters repopulating.

### 4.3 Chroma Restore

1. Quiesce backend writes (scale to zero replicas or `docker compose stop backend`).
2. Retrieve backup archive:
    ```bash
    az storage blob download --account-name auraiaops --container-name chroma \
      --name chroma-202510191200.tgz --file /tmp/chroma.tgz
    tar -xzf /tmp/chroma.tgz -C /tmp/chroma-restore
    ```
3. Replace volume contents:
    ```bash
    docker run --rm \
      -v backend_chroma_data:/data \
      -v /tmp/chroma-restore:/restore \
      alpine sh -c 'rm -rf /data/* && cp -r /restore/. /data/'
    ```
4. Restart backend and perform semantic search smoke test (`/api/search/test`).

---

## 5. Post-Recovery Checklist

- [ ] Backend `/health` endpoint reports `healthy: true`.
- [ ] Prometheus targets `backend`, `redis`, `ollama` show `UP` status inside 5 minutes.
- [ ] Grafana latency + rate limit panels display current data without gaps.
- [ ] VS Code extension completes generate/explain flows against restored environment.
- [ ] Incident ticket updated with timeline, data loss (if any), root cause, and action items.

---

## 6. Readiness & Testing

- Run quarterly DR drills validating Redis + Chroma restore duration and document RTO/RPO results.
- Schedule nightly integrity checks: `redis-cli --scan | head` (sanity) and `sqlite3 chroma.sqlite3 "PRAGMA integrity_check;"`.
- Alert if `redis_connected_clients` < 1 for 5 minutes or backend `/health` fails 3 consecutive probes (see Prometheus alert rules).

---

## 7. Reference Diagram

```
VS Code Extension -> FastAPI Backend -> Redis (AOF snapshots)
                                              -> Chroma (persistent volume snapshots)
```

---

## Change History

| Date       | Change | Author |
|------------|--------|--------|
| 2025-10-19 | Introduced enterprise-grade DR procedures for Redis and Chroma | GitHub Copilot |
