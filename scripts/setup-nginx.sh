#!/usr/bin/env bash
set -euo pipefail

SITE_CONF="deploy/nginx/siren-webhook"
SITES_AVAILABLE="/etc/nginx/sites-available/siren-webhook"
SITES_ENABLED="/etc/nginx/sites-enabled/siren-webhook"

cd "$(dirname "$0")/.."

if ! command -v nginx &>/dev/null; then
  echo "nginx not found — installing..."
  sudo apt-get update -qq
  sudo apt-get install -y nginx
fi

echo "Copying site config to $SITES_AVAILABLE..."
sudo cp "$SITE_CONF" "$SITES_AVAILABLE"
sudo chmod 644 "$SITES_AVAILABLE"

if [[ ! -L "$SITES_ENABLED" ]]; then
  sudo ln -s "$SITES_AVAILABLE" "$SITES_ENABLED"
fi

echo "Testing nginx config..."
sudo nginx -t

echo "Reloading nginx..."
sudo systemctl enable --now nginx
sudo systemctl reload nginx

echo "Done. nginx is proxying POST /trigger → localhost:8000"
