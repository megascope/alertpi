#!/usr/bin/env bash
set -euo pipefail

app_dir="/opt/siren-driver"
config_dir="/etc/siren-driver"
unit_name="internet-led-watchdog.service"
unit_path="/etc/systemd/system/$unit_name"
purge=false

usage() {
  cat <<'EOF'
Usage: scripts/internet-watchdog-uninstall.sh [options]

Removes the internet LED watchdog systemd unit. By default, leaves installed
files and config in place.

Options:
  --app-dir <path>      App install directory (default: /opt/siren-driver)
  --config-dir <path>   Config directory (default: /etc/siren-driver)
  --purge               Also remove the watchdog script and env file
  -h, --help            Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dir)
      app_dir="${2:-}"
      shift 2
      ;;
    --config-dir)
      config_dir="${2:-}"
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
  echo "error: run this script as root (for example: sudo ./scripts/internet-watchdog-uninstall.sh)" >&2
  exit 1
fi

systemctl disable --now "$unit_name" 2>/dev/null || true
rm -f "$unit_path"
systemctl daemon-reload
systemctl reset-failed

if [[ "$purge" == true ]]; then
  rm -f "$app_dir/src/watchdog/internet_led_watchdog.py" "$app_dir/src/watchdog/__init__.py"
  rmdir "$app_dir/src/watchdog" 2>/dev/null || true
  rm -f "$config_dir/internet-led-watchdog.env"
fi

echo "Removed $unit_name"
if [[ "$purge" == true ]]; then
  echo "Purged watchdog script and env file."
fi
