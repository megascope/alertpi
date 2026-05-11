#!/usr/bin/env bash
set -euo pipefail

unit_dir=${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd
env_dir=${XDG_CONFIG_HOME:-$HOME/.config}/siren-webhook

mkdir -p "$unit_dir" "$env_dir"
cp deploy/quadlet/siren-webhook.container "$unit_dir/siren-webhook.container"

if [[ ! -f "$env_dir/siren-webhook.env" ]]; then
  cp .env.example "$env_dir/siren-webhook.env"
fi

current_user=${USER:-$(id -un)}
linger_state=$(loginctl show-user "$current_user" -p Linger --value 2>/dev/null || echo "")
if [[ "$linger_state" != "yes" ]]; then
  echo "Enabling linger for user '$current_user' (requires sudo)..."
  sudo loginctl enable-linger "$current_user"
fi

systemctl --user daemon-reload
systemctl --user enable --now siren-webhook.service
