#!/bin/sh
set -e
echo "[ALEMBIC] MIGRATE::HEAD"
alembic upgrade head
echo "[APP] RUN AGENT"
exec uvicorn src.presentation.api.main:create_app --factory \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --timeout-graceful-shutdown 15
