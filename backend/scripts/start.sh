#!/bin/sh
set -e

# Run database migrations before serving traffic (unless explicitly disabled)
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "[start.sh] Executing database migrations..."
    python -m app.db.migrate
    echo "[start.sh] Migrations successfully finished."
else
    echo "[start.sh] Skipping database migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS})."
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-2}"

echo "[start.sh] Starting Uvicorn on ${HOST}:${PORT} with ${WORKERS} worker(s)..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
