#!/usr/bin/env bash
# Copy a full local Postgres database into Neon (replaces objects in target DB).
#
# Prerequisites: Homebrew Postgres client (pg_dump / pg_restore) on PATH.
# Neon: use a DIRECT connection URI (hostname must NOT contain "-pooler").
#       Pooler rejects pg_restore and some startup options — see:
#       https://neon.tech/docs/import/migrate-from-postgres
#
# Usage (from your laptop, with source Postgres reachable):
#   export LOCAL_POSTGRES_URL='postgresql://USER:PASS@127.0.0.1:5432/your_local_db'
#   export NEON_DIRECT_URL='postgresql://neondb_owner:PASS@ep-xxx.c-6.region.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
#   ./scripts/pg_local_to_neon.sh
#
# Supabase (legacy): pooler host often works for pg_dump on port 5432, e.g.
#   postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
# Restore to Neon may report many ignored errors (Supabase roles/ACLs); check row counts after.
# To limit dump to Django tables only next time: add -n public to pg_dump below (edit script).
#
# WARNING: This runs pg_restore --clean --if-exists on NEON_DIRECT_URL and will
#          drop/replace objects in that database. Back up Neon first if unsure.

set -euo pipefail

: "${LOCAL_POSTGRES_URL:?Set LOCAL_POSTGRES_URL to your local Postgres URI}"
: "${NEON_DIRECT_URL:?Set NEON_DIRECT_URL to Neon DIRECT (non-pooler) URI}"

if [[ "$NEON_DIRECT_URL" == *"-pooler"* ]]; then
  echo "ERROR: NEON_DIRECT_URL must use the direct host (no '-pooler')." >&2
  echo "In Neon Console → Connect, disable connection pooling or strip '-pooler' from the hostname." >&2
  exit 1
fi

DUMP="$(mktemp -t tribunal_pg_XXXXXX.dump)"
trap 'rm -f "$DUMP"' EXIT

echo "==> pg_dump from local (custom format)..."
pg_dump -Fc -v -d "$LOCAL_POSTGRES_URL" -f "$DUMP"

echo "==> pg_restore into Neon (destructive: --clean --if-exists)..."
pg_restore -v -O --no-tablespaces --clean --if-exists -d "$NEON_DIRECT_URL" "$DUMP"

echo "==> Done. On backend-api: uv run python manage.py migrate && uv run python manage.py check"
