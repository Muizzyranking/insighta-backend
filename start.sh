#!/bin/bash
set -e

echo "Running Database Migrations..."
uv run alembic upgrade head

echo "Starting FastAPI Server..."
PORT=${PORT:-8000}

uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
