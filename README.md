# GRC Service

Foundational Django microservice for Governance, Risk, and Compliance capabilities focusing on the Internal Audit module. This service follows the same patterns used across other FIMS backend services (IAM, Document Records, Work Orchestration) and exposes read-only endpoints for audit testers.

## Features

- Django 4.2 + DRF skeleton with health and audit list APIs
- Kafka-powered permission registration with IAM
- Dockerized runtime with PostgreSQL, Redis, Gunicorn, and Celery workers
- Sample audit data to unblock frontend integration until full persistence is available

## Getting Started

```bash
cp env.example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8006
```

### Docker Compose

```bash
docker compose up --build
```

This brings up:
- `postgres-grc-service` (PostgreSQL 15)
- `redis-grc-service` (Redis 7)
- `grc-service` (Gunicorn + Django)
- `grc-celery-worker` & `grc-celery-beat`

### Registering Permissions

After the service is up, publish IAM permissions over Kafka:

```bash
python manage.py register_permissions_kafka
```

## API

- `GET /health/` – health probe
- `GET /api/v1/grc/audit/plans/` – sample audit plans
- `GET /api/v1/grc/audit/engagements/` – sample audit engagements
- `GET /api/v1/grc/audit/monitoring/` – sample recommendation monitoring entries

## Folder Structure

```
apps/
  api/              # REST endpoints & routing
  core/             # Permissions, Kafka clients, shared helpers
config/
  settings.py       # Django settings with env-driven config
  urls.py           # Routes /api/v1/grc/* to API module
scripts/init-db/    # Postgres initialization helpers
```

## Next Steps

- Replace sample data with PostgreSQL models
- Extend API surface according to `implementation/GRC_AUDIT_SERVICE_DESIGN.md`
- Wire Celery pipelines for monitoring reminders
- Harden observability (metrics, tracing)
