#!/usr/bin/env bash
set -euo pipefail

image_name=${1:-ghcr.io/megascope/alertpi/siren-webhook:latest}

# Get gpio group GID dynamically from host
gpio_gid=$(getent group gpio | cut -d: -f3)
if [[ -z "$gpio_gid" ]]; then
  echo "ERROR: gpio group not found on host. Run: sudo groupadd gpio && sudo usermod -aG gpio $USER"
  exit 1
fi

podman run --rm -it \
  --name siren-webhook \
  -p 8000:8000 \
  --device /dev/gpiomem \
  --device /dev/gpiochip0 \
  --group-add "$gpio_gid" \
  --env-file .env \
  "$image_name"
