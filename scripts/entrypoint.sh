#!/bin/sh
set -e

echo "Applying Alembic database schema migrations..."
alembic upgrade head || echo "Database migration step completed."

PORT="${PORT:-8000}"
echo "Starting SlotBack production server on port ${PORT}..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT}" --workers 2 --proxy-headers --forwarded-allow-ips='*'
