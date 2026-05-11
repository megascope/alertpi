#!/usr/bin/env bash
set -euo pipefail

unit_dir=${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd
env_dir=${XDG_CONFIG_HOME:-$HOME/.config}/siren-webhook
service_name=siren-webhook.service
quadlet_name=siren-webhook.container
wants_dir="$unit_dir/default.target.wants"

mkdir -p "$unit_dir" "$env_dir" "$wants_dir"

# Get gpio group GID dynamically from host
gpio_gid=$(getent group gpio | cut -d: -f3)
if [[ -z "$gpio_gid" ]]; then
  echo "ERROR: gpio group not found on host. Run: sudo groupadd gpio && sudo usermod -aG gpio $USER"
  exit 1
fi

# Copy quadlet and substitute gpio GID
sed "s/GroupAdd=986/GroupAdd=$gpio_gid/g" deploy/quadlet/siren-webhook.container > "$unit_dir/$quadlet_name"

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

if ! systemctl --user list-unit-files --type=service --all | grep -q "^${service_name}"; then
  echo "ERROR: ${service_name} was not generated from quadlet."
  echo "Ensure Podman with quadlet support is installed, then rerun this script."
  echo "Debug commands:"
  echo "  podman --version"
  echo "  systemctl --user --no-pager list-unit-files | grep siren-webhook"
  exit 1
fi

# Enabling generated units directly fails; enable quadlet by symlinking it into
# default.target.wants and then start the generated service.
ln -sf "../$quadlet_name" "$wants_dir/$quadlet_name"
systemctl --user start "$service_name"
