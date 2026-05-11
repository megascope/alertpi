#!/usr/bin/env bash
set -euo pipefail

service_user="siren"
home_dir="/var/lib/siren-driver"
config_dir="/etc/siren-driver"
app_dir="/opt/siren-driver"
unit_name="siren-driver.service"
unit_path="/etc/systemd/system/$unit_name"
purge=false

usage() {
  cat <<'EOF'
Usage: scripts/systemd-uninstall.sh [options]

Removes the host systemd unit for the siren driver. By default, leaves the
service user, app files, and env file in place.

Options:
  --user <name>         Service user name (default: siren)
  --home <path>         Service state directory (default: /var/lib/siren-driver)
  --config-dir <path>   Config directory (default: /etc/siren-driver)
  --app-dir <path>      App install directory (default: /opt/siren-driver)
  --purge               Also remove app/config directories and delete the user
  -h, --help            Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      service_user="${2:-}"
      shift 2
      ;;
    --home)
      home_dir="${2:-}"
      shift 2
      ;;
    --config-dir)
      config_dir="${2:-}"
      shift 2
      ;;
    --app-dir)
      app_dir="${2:-}"
      shift 2
      ;;
    --purge)
      purge=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option '$1'" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$EUID" -ne 0 ]]; then
  echo "error: run this script as root (for example: sudo ./scripts/systemd-uninstall.sh)" >&2
  exit 1
fi

systemctl disable --now "$unit_name" 2>/dev/null || true
rm -f "$unit_path"
systemctl daemon-reload
systemctl reset-failed

if [[ "$purge" == true ]]; then
  rm -rf "$app_dir" "$config_dir" "$home_dir"
  if id -u "$service_user" >/dev/null 2>&1; then
    userdel "$service_user" 2>/dev/null || true
  fi
fi

echo "Removed $unit_name"
if [[ "$purge" == true ]]; then
  echo "Purged app/config/state paths and attempted to delete user '$service_user'."
fi
