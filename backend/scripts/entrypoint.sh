#!/bin/bash
set -e

echo "=== LangNovel Studio Starting ==="

# Wait for database
echo "Waiting for database..."
RETRIES=30
until pg_isready -h db -U langnovel -d langnovel_db 2>/dev/null; do
  RETRIES=$((RETRIES - 1))
  if [ $RETRIES -le 0 ]; then
    echo "ERROR: Database not available after 60 seconds. Exiting."
    exit 1
  fi
  echo "  Database not ready yet, retrying... ($RETRIES attempts left)"
  sleep 2
done
echo "Database is ready."

# Run migrations
echo "Running database migrations..."
cd /app
export PYTHONPATH="/app:${PYTHONPATH}"
alembic upgrade head

# Start the application
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
