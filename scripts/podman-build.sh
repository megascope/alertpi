#!/usr/bin/env bash
set -euo pipefail

image_name=${1:-localhost/siren-webhook:latest}

podman build -t "$image_name" -f container/Containerfile .
