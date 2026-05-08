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

# Step 1: Start Nginx with HTTP-only config for ACME challenge
echo "[1/3] Starting Nginx for ACME challenge..."

# Create temporary Nginx config (HTTP only)
cat > /tmp/nginx-temp.conf << 'EOF'
server {
    listen 80;
    server_name _;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 'OK'; add_header Content-Type text/plain; }
}
EOF

docker compose -f docker-compose.prod.yml up -d nginx

# Step 2: Request certificate
echo "[2/3] Requesting certificate from Let's Encrypt..."
docker compose -f docker-compose.prod.yml run --rm certbot \
    certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${DOMAIN}"

# Step 3: Restart Nginx with SSL config
echo "[3/3] Restarting Nginx with SSL..."
docker compose -f docker-compose.prod.yml restart nginx

echo ""
echo "SSL certificate installed for ${DOMAIN}"
echo "Certificate will auto-renew via the certbot container."
