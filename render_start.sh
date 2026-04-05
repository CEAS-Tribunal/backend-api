#!/usr/bin/env bash
# Render start: migrate then Gunicorn on $PORT — https://render.com/docs/web-services#port-binding
set -o errexit
set -o pipefail

python manage.py migrate --noinput
exec gunicorn backendapi.wsgi:application --bind "0.0.0.0:${PORT:-10000}"
