#!/usr/bin/env bash
set -euo pipefail

image_name=${1:-localhost/siren-webhook:latest}

podman run --rm -it \
  --name siren-webhook \
  -p 8000:8000 \
  --device /dev/gpiomem \
  --group-add gpio \
  --env-file .env \
  "$image_name"
