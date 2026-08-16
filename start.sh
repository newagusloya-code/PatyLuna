#!/usr/bin/env bash
set -e

if [ -f "alembic.ini" ]; then
    echo "Running database migrations via Alembic..."
    alembic upgrade head
else
    echo "Alembic not initialized; database schemas managed automatically via lifespan startup."
fi

echo "Starting Uvicorn..."
# Use Uvicorn with Gunicorn for production, binding to 0.0.0.0:$PORT
# Render provides the $PORT environment variable automatically.
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --access-logfile - --error-logfile -
