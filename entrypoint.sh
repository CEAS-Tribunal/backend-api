#!/bin/bash

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start development server
echo "Starting development server..."
exec python manage.py runserver 0.0.0.0:8000