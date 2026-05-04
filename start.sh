#!/usr/bin/env bash
set -e

echo "--- Checking Superuser Status ---"
python manage.py create_superuser_if_not_exists

echo "--- Launching Gunicorn ---"
# 'exec' replaces the shell with the gunicorn process for better signal handling
exec gunicorn luxe_backend.wsgi:application --bind 0.0.0.0:$PORT