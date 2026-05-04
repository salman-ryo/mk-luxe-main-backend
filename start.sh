#!/usr/bin/env bash
set -e

python manage.py migrate
python manage.py create_superuser_if_not_exists

exec gunicorn luxe_backend.wsgi:application --bind 0.0.0.0:$PORT