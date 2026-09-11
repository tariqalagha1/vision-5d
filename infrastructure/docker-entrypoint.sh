#!/bin/bash
# Vision 5D — Docker Entrypoint
# Handles: api, worker, migrate, backup, health-check modes

set -e

echo "[vision5d] Starting in mode: ${1:-api}"
echo "[vision5d] Environment: ${V5D_ENV:-production}"

# ── Database migration ──
if [ "${V5D_AUTO_MIGRATE:-true}" = "true" ]; then
    echo "[vision5d] Running database migrations..."
    cd /app && python3 -c "
import sys
sys.path.insert(0, '/app')
from alembic.config import Config
from alembic import command
try:
    alembic_cfg = Config('/app/alembic.ini')
    command.upgrade(alembic_cfg, 'head')
    print('[vision5d] Migrations complete')
except Exception as e:
    print(f'[vision5d] Migration error: {e}')
    # Don't fail startup for migration issues — may be first run
"
fi

# ── Mode dispatch ──
case "${1}" in
    api)
        echo "[vision5d] Starting API server on port ${PORT:-8000}"
        exec python3 -m uvicorn apps.api.main:app \
            --host 0.0.0.0 \
            --port ${PORT:-8000} \
            --workers ${API_WORKERS:-4} \
            --log-level ${LOG_LEVEL:-info} \
            --timeout-keep-alive 30 \
            --limit-concurrency ${API_CONCURRENCY:-100} \
            --limit-max-requests ${API_MAX_REQUESTS:-10000}
        ;;
    worker)
        echo "[vision5d] Starting durable worker"
        exec python3 apps/worker/main.py
        ;;
    migrate)
        echo "[vision5d] Running migrations only"
        cd /app && python3 -c "
from alembic.config import Config
from alembic import command
alembic_cfg = Config('/app/alembic.ini')
command.upgrade(alembic_cfg, 'head')
"
        echo "[vision5d] Migrations complete"
        ;;
    backup)
        echo "[vision5d] Running backup..."
        exec python3 infrastructure/backup.py
        ;;
    shell)
        exec /bin/bash
        ;;
    *)
        echo "[vision5d] Unknown mode: ${1}"
        echo "Usage: entrypoint [api|worker|migrate|backup|shell]"
        exit 1
        ;;
esac
