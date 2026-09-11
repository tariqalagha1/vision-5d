#!/bin/bash
# Vision 5D — Production Deployment Script
# Usage: bash infrastructure/deploy.sh [up|down|restart|logs|status|backup]

set -e
cd "$(dirname "$0")/.."

COMPOSE_FILE="infrastructure/docker-compose.yml"
ENV_FILE=".env.production"

case "${1:-up}" in
    up)
        echo "[deploy] Starting Vision 5D production deployment..."
        if [ -f "$ENV_FILE" ]; then
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
        else
            echo "[deploy] WARNING: $ENV_FILE not found. Using defaults."
            docker compose -f "$COMPOSE_FILE" up -d --build
        fi
        echo "[deploy] Waiting for services to be healthy..."
        sleep 10
        docker compose -f "$COMPOSE_FILE" ps
        echo "[deploy] Deployment complete. API: http://localhost:${API_PORT:-8000}"
        ;;
    down)
        docker compose -f "$COMPOSE_FILE" down
        echo "[deploy] Services stopped"
        ;;
    restart)
        docker compose -f "$COMPOSE_FILE" restart
        echo "[deploy] Services restarted"
        ;;
    logs)
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100
        ;;
    status)
        docker compose -f "$COMPOSE_FILE" ps
        curl -s http://localhost:${API_PORT:-8000}/health | python3 -m json.tool 2>/dev/null || echo "API not responding"
        ;;
    backup)
        echo "[deploy] Running backup..."
        docker compose -f "$COMPOSE_FILE" exec -T api python3 infrastructure/backup.py
        ;;
    migrate)
        echo "[deploy] Running migrations..."
        docker compose -f "$COMPOSE_FILE" run --rm api migrate
        ;;
    *)
        echo "Usage: deploy.sh [up|down|restart|logs|status|backup|migrate]"
        exit 1
        ;;
esac
