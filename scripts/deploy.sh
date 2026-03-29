#!/bin/bash
# AIGITO production deploy script
# Usage: ./scripts/deploy.sh

set -e

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "=== AIGITO Deploy ==="
echo ""

# Ensure .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env not found. Copy .env.example and fill in values."
    exit 1
fi

echo "Pulling latest code..."
git pull origin "$(git branch --show-current)"

echo "Building images..."
$COMPOSE build --no-cache

echo "Starting databases first..."
$COMPOSE up -d postgres redis qdrant

echo "Waiting for postgres to be ready..."
until $COMPOSE exec postgres pg_isready -U aigita -d aigita; do
    sleep 2
done

echo "Running database migrations..."
$COMPOSE run --rm backend alembic upgrade head

echo "Starting all services..."
$COMPOSE up -d

echo ""
echo "=== Services status ==="
$COMPOSE ps

echo ""
echo "=== Checking health ==="
sleep 5
curl -sf http://localhost:8000/health && echo "Backend: OK" || echo "Backend: FAIL"
curl -sf http://localhost:6333/healthz && echo "Qdrant: OK" || echo "Qdrant: FAIL"

echo ""
echo "Deploy complete!"
