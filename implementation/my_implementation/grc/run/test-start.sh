#!/usr/bin/env bash
# Start only minimal services required for GRC testing

set -e

FIMS="$(cd "$(dirname "$0")" && pwd)"

echo "==> [1/7] Starting Message Broker..."
docker compose -f "$FIMS/message-broker/docker-compose.yml" up -d --no-deps \
  zookeeper \
  kafka

echo "==> [2/7] Starting IAM Service..."
docker compose -f "$FIMS/iam-service/docker-compose.yml" up -d --no-deps \
  postgres-iam-service \
  redis-iam-service \
  iam-service

echo "==> [3/7] Starting API Gateway..."
docker compose -f "$FIMS/api-gateway/docker-compose.yml" up -d --no-deps \
  api-gateway

echo "==> [4/7] Starting Document Records Service..."
docker compose -f "$FIMS/document-records-service/docker-compose.yml" up -d --no-deps \
  postgres-document-records-service \
  redis-document-records-service \
  document-records-service \
  document-celery-worker \
  document-celery-beat \
  document-kafka-consumer

echo "==> [5/7] Starting GRC Service..."
docker compose -f "$FIMS/grc-service/docker-compose.yml" up -d --no-deps \
  postgres-grc-service \
  redis-grc-service \
  grc-service \
  grc-celery-worker \
  grc-celery-beat \
  grc-kafka-consumer

echo "==> [6/7] Starting Work Orchestration Service..."
docker compose -f "$FIMS/work-orchestration-service/docker-compose.yml" up -d --no-deps \
  postgres-work-orchestration-service \
  redis-work-orchestration-service \
  work-orchestration-service \
  work-orchestration-celery \
  work-orchestration-celery-beat \
  work-orchestration-kafka-consumer

echo "==> [7/7] Starting Frontend..."
docker compose -f "$FIMS/frontend/docker-compose.yml" up -d --no-deps \
  staff-portal

echo ""
echo "All required testing services started."
echo ""
echo "Frontend (staff)  →  http://localhost:3001"
echo "API Gateway       →  http://localhost:8080"
echo "IAM Service       →  http://localhost:8000"
echo "GRC Service       →  http://localhost:8006"
echo "Work Orch Service →  http://localhost:8004"
echo "Doc Records       →  http://localhost:8002"
