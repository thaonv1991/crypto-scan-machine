#!/bin/bash
# Initialize SSL certificates with Let's Encrypt
# Usage: ./scripts/init-ssl.sh your-domain.com admin@your-domain.com
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> <email>}"
EMAIL="${2:?Usage: $0 <domain> <email>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

cd "${PROJECT_DIR}"

echo "Initializing SSL for domain: ${DOMAIN}"

# Create directories
mkdir -p certbot/conf certbot/www

# Update Nginx config with real domain
sed -i "s/server_name _;/server_name ${DOMAIN};/g" nginx/conf.d/default.conf
sed -i "s|/etc/letsencrypt/live/cryptoscan/|/etc/letsencrypt/live/${DOMAIN}/|g" nginx/conf.d/default.conf

# Step 1: Generate self-signed cert as placeholder so Nginx can start with the SSL block
echo "[1/4] Generating temporary self-signed certificate..."
mkdir -p "certbot/conf/live/${DOMAIN}"
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "certbot/conf/live/${DOMAIN}/privkey.pem" \
    -out "certbot/conf/live/${DOMAIN}/fullchain.pem" \
    -subj "/CN=${DOMAIN}" 2>/dev/null

# Step 2: Start Nginx (HTTP server works, SSL block uses temp cert)
echo "[2/4] Starting Nginx..."
docker compose -f docker-compose.prod.yml up -d nginx
sleep 3

# Step 3: Request real certificate from Let's Encrypt
echo "[3/4] Requesting certificate from Let's Encrypt..."
docker compose -f docker-compose.prod.yml run --rm certbot \
    certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "${DOMAIN}"

# Step 4: Restart Nginx to load real certificate
echo "[4/4] Restarting Nginx with real SSL certificate..."
docker compose -f docker-compose.prod.yml restart nginx

echo ""
echo "SSL certificate installed for ${DOMAIN}"
echo "Certificate will auto-renew via the certbot container."
