# Variables
PYTHON = python3
MANAGE = $(PYTHON) manage.py
PIP = pip install -r requirements.txt
GUNICORN = gunicorn luxe_backend.wsgi:application --bind 0.0.0.0:$(PORT)

.PHONY: build start migrate static superuser help

# ---------------------------------------------------------
# RENDER COMMANDS
# ---------------------------------------------------------

# The Build Command for Render
build:
	@echo "--- Starting Build Process ---"
	$(PIP)
	$(MANAGE) collectstatic --no-input
	$(MANAGE) migrate
	@echo "--- Build Complete ---"

# The Start Command for Render
start:
	@echo "--- Starting Application ---"
	$(MANAGE) migrate
	$(MANAGE) create_superuser_if_not_exists
	$(GUNICORN)

# ---------------------------------------------------------
# UTILITY COMMANDS (For Local Development)
# ---------------------------------------------------------

migrate:
	$(MANAGE) makemigrations
	$(MANAGE) migrate

static:
	$(MANAGE) collectstatic --no-input

superuser:
	$(MANAGE) createsuperuser

help:
	@echo "Available targets:"
	@echo "  make build      - Install deps, collectstatic, and migrate"
	@echo "  make start      - Run migrations, create superuser, and launch Gunicorn"
	@echo "  make migrate    - Run local migrations"
	@echo "  make static     - Collect static files locally"