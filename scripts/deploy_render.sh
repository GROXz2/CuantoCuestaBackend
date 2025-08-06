#!/usr/bin/env bash
set -euo pipefail

# Ensure required environment variables are set
: "${OPENAI_API_KEY:?OPENAI_API_KEY no está definido}"
: "${DATABASE_URL:?DATABASE_URL no está definido}"
: "${REDIS_URL:?REDIS_URL no está definido}"

# Run database migrations
alembic upgrade head
