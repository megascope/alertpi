#!/usr/bin/env bash
set -euo pipefail

unit_dir=${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd
env_dir=${XDG_CONFIG_HOME:-$HOME/.config}/siren-webhook

mkdir -p "$unit_dir" "$env_dir"
cp deploy/quadlet/siren-webhook.container "$unit_dir/siren-webhook.container"

if [[ ! -f "$env_dir/siren-webhook.env" ]]; then
  cp .env.example "$env_dir/siren-webhook.env"
fi

systemctl --user daemon-reload
systemctl --user enable --now siren-webhook.service
