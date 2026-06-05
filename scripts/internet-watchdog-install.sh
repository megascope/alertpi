#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
app_dir="/opt/siren-driver"
config_dir="/etc/siren-driver"
unit_name="internet-led-watchdog.service"
unit_path="/etc/systemd/system/$unit_name"

usage() {
  cat <<'EOF'
Usage: scripts/internet-watchdog-install.sh [options]

Installs a root systemd service that blinks SOS on the Raspberry Pi green ACT LED
while internet connectivity checks are failing.

Options:
  --app-dir <path>      App install directory (default: /opt/siren-driver)
  --config-dir <path>   Config directory (default: /etc/siren-driver)
  -h, --help            Show this help message

Optional config file:
  /etc/siren-driver/internet-led-watchdog.env

Supported environment variables:
  INTERNET_WATCHDOG_LED=/sys/class/leds/led0
  INTERNET_WATCHDOG_PROBES=1.1.1.1:443,8.8.8.8:53
  INTERNET_WATCHDOG_INTERVAL_SECONDS=10
  INTERNET_WATCHDOG_TIMEOUT_SECONDS=3
  INTERNET_WATCHDOG_FAIL_THRESHOLD=3
  INTERNET_WATCHDOG_MORSE_UNIT_SECONDS=0.2

Test the LED pattern after install:
  sudo /usr/bin/python3 /opt/siren-driver/src/watchdog/internet_led_watchdog.py --test
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
  echo "error: run this script as root (for example: sudo ./scripts/internet-watchdog-install.sh)" >&2
  exit 1
fi

install -d -o root -g root -m 0755 "$app_dir/src/watchdog"
install -d -o root -g root -m 0755 "$config_dir"
install -o root -g root -m 0644 "$repo_root/src/watchdog/__init__.py" "$app_dir/src/watchdog/__init__.py"
install -o root -g root -m 0755 "$repo_root/src/watchdog/internet_led_watchdog.py" "$app_dir/src/watchdog/internet_led_watchdog.py"

env_file="$config_dir/internet-led-watchdog.env"
if [[ ! -f "$env_file" ]]; then
  cat > "$env_file" <<'EOF'
# Optional overrides for internet-led-watchdog.service.
# INTERNET_WATCHDOG_LED=/sys/class/leds/led0
# INTERNET_WATCHDOG_PROBES=1.1.1.1:443,8.8.8.8:53
# INTERNET_WATCHDOG_INTERVAL_SECONDS=10
# INTERNET_WATCHDOG_TIMEOUT_SECONDS=3
# INTERNET_WATCHDOG_FAIL_THRESHOLD=3
# INTERNET_WATCHDOG_MORSE_UNIT_SECONDS=0.2
EOF
  chmod 0644 "$env_file"
fi

sed \
  -e "s|{{APP_DIR}}|$app_dir|g" \
  -e "s|{{ENV_FILE}}|$env_file|g" \
  "$repo_root/deploy/systemd/internet-led-watchdog.service" > "$unit_path"

chmod 0644 "$unit_path"
systemctl daemon-reload
systemctl enable --now "$unit_name"

echo "Installed $unit_name"
echo "- app dir: $app_dir"
echo "- env file: $env_file"
echo
echo "Check status with: systemctl status $unit_name --no-pager"
