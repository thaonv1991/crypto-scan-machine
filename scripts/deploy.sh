#!/bin/bash
# CryptoScan Machine - Production Deployment Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

echo "=========================================="
echo "  CryptoScan Machine - Production Deploy  "
echo "=========================================="

cd "${PROJECT_DIR}"

# Check .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and configure all required values."
    exit 1
fi

# Check required environment variables
echo "[1/7] Checking configuration..."
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "TELEGRAM_BOT_TOKEN"
    "DEEPSEEK_API_KEY"
)

MISSING=0
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env || [ -z "$(grep "^${var}=" .env | cut -d'=' -f2-)" ]; then
        echo "  WARNING: ${var} is not set in .env"
        MISSING=$((MISSING + 1))
    fi
done

if [ ${MISSING} -gt 0 ]; then
    echo "  ${MISSING} variable(s) missing. System may not function fully."
fi

# Create required directories
echo "[2/7] Creating directories..."
mkdir -p backups certbot/conf certbot/www nginx/conf.d

# Generate self-signed cert if no SSL certs exist (so Nginx can start)
if [ ! -f certbot/conf/live/cryptoscan/fullchain.pem ]; then
    echo "  Generating self-signed placeholder certificate for Nginx..."
    mkdir -p certbot/conf/live/cryptoscan
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout certbot/conf/live/cryptoscan/privkey.pem \
        -out certbot/conf/live/cryptoscan/fullchain.pem \
        -subj "/CN=localhost" 2>/dev/null
    echo "  Self-signed cert created. Run init-ssl.sh later for real certs."
fi

# Pull latest images
echo "[3/7] Pulling latest images..."
docker compose -f docker-compose.prod.yml pull

# Build application image
echo "[4/7] Building application..."
docker compose -f docker-compose.prod.yml build --no-cache api

# Stop existing services
echo "[5/7] Stopping existing services..."
docker compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

# Start all services
echo "[6/7] Starting services..."
docker compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo ""
echo "Waiting for services to start..."
sleep 10

# Health check
echo "[7/7] Running health checks..."

API_STATUS=$(curl -sf http://localhost:8000/health 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unreachable")
echo "  API:       ${API_STATUS}"

REDIS_STATUS=$(docker exec cryptoscan-redis redis-cli ping 2>/dev/null || echo "unreachable")
echo "  Redis:     ${REDIS_STATUS}"

PG_STATUS=$(docker exec cryptoscan-postgres pg_isready -U cryptoscan 2>/dev/null && echo "ready" || echo "unreachable")
echo "  Postgres:  ${PG_STATUS}"

echo ""
echo "=========================================="
echo "  Deployment complete!                    "
echo "=========================================="
echo ""
echo "Services:"
echo "  API:        http://localhost:8000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  Flower:     http://localhost:5555"
echo "  Grafana:    http://localhost:3000"
echo "  Prometheus: http://localhost:9090"
echo ""
echo "Run database migrations:"
echo "  docker exec cryptoscan-api alembic upgrade head"
echo ""
echo "View logs:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
