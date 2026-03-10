#!/usr/bin/env bash
# rebuild-prep.sh — Stop all non-essential services before rebuilding.
#
# Keeps running (do NOT touch):
#   iam-service       — required by api-gateway for auth
#   message-broker    — required by kafka consumers on restart
#   api-gateway       — required to route requests
#
# Stops (safe to stop during rebuild):
#   frontend
#   grc-service
#   work-orchestration-service
#   document-records-service
#
# Data volumes are preserved (--volumes is NOT passed) — only containers are removed.
#
# Usage: ./rebuild-prep.sh

set -e

FIMS="$(cd "$(dirname "$0")" && pwd)"

echo "==> Removing Frontend..."
docker compose -f "$FIMS/frontend/docker-compose.yml" down

echo "==> Removing GRC Service..."
docker compose -f "$FIMS/grc-service/docker-compose.yml" down

echo "==> Removing Work Orchestration Service..."
docker compose -f "$FIMS/work-orchestration-service/docker-compose.yml" down

echo "==> Removing Document Records Service..."
docker compose -f "$FIMS/document-records-service/docker-compose.yml" down

echo ""
echo "Ready to rebuild. Still running:"
echo "  - IAM Service   (fims-iam-service + postgres + redis + kafka-consumer)"
echo "  - Message Broker (fims-kafka + fims-zookeeper)"
echo "  - API Gateway   (fims-api-gateway)"
echo ""
echo "After rebuilding, run ./test-start.sh to bring everything back up."
