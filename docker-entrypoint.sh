#!/bin/bash
# GRC Service Docker Entrypoint
# Handles infrastructure-level startup tasks before the application server.
# Permission registration is NOT done here — it runs automatically inside
# apps.py CoreConfig.ready() on every gunicorn worker startup, following
# the same pattern used by WO and Document Records services.

set -e

echo "==> [GRC] Running database migrations..."
python manage.py migrate --noinput

echo "==> [GRC] Collecting static files..."
python manage.py collectstatic --noinput

echo "==> [GRC] Starting application server..."
exec "$@"
