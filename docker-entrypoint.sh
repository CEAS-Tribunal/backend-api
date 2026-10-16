#!/bin/sh
set -eu

# Named volumes for media/static are often root-owned. Fix ownership, then
# re-exec as the non-root app user before migrate / the server process.
if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/media /app/static
  chown -R app:app /app/media /app/static
  exec runuser -u app -- "$0" "$@"
fi

python manage.py migrate --noinput

exec "$@"
