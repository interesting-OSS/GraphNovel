#!/bin/bash
set -e

echo "=== GraphNovel Container Starting ==="
echo "Running database migrations..."
cd /app
alembic upgrade head
echo "Migrations complete."

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
