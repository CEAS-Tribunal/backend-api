#!/usr/bin/env bash
# Render build step — https://render.com/docs/deploy-django
set -o errexit
set -o pipefail

pip install -r requirements.txt
python manage.py collectstatic --noinput --clear
