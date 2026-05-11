#!/usr/bin/env bash
set -euo pipefail

service_user="siren"
home_dir="/var/lib/siren-driver"
config_dir="/etc/siren-driver"

usage() {
  cat <<'EOF'
Usage: scripts/setup-siren-user.sh [options]

Creates a locked-down service account for running the siren driver directly on
the Raspberry Pi host instead of inside a container.

Options:
  --user <name>         Service user name (default: siren)
  --home <path>         Service home/data directory (default: /var/lib/siren-driver)
  --config-dir <path>   Config directory for env file (default: /etc/siren-driver)
  -h, --help            Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      service_user="${2:-}"
      if [[ -z "$service_user" ]]; then
        echo "error: --user requires a value" >&2
        exit 2
      fi
      shift 2
      ;;
    --home)
      home_dir="${2:-}"
      if [[ -z "$home_dir" ]]; then
        echo "error: --home requires a value" >&2
        exit 2
      fi
      shift 2
      ;;
    --config-dir)
      config_dir="${2:-}"
      if [[ -z "$config_dir" ]]; then
        echo "error: --config-dir requires a value" >&2
        exit 2
      fi
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
  echo "error: run this script as root (for example: sudo ./scripts/setup-siren-user.sh)" >&2
  exit 1
fi

if ! getent group gpio >/dev/null 2>&1; then
  echo "error: host group 'gpio' does not exist" >&2
  exit 1
fi

nologin_shell=""
for candidate in /usr/sbin/nologin /usr/bin/nologin; do
  if [[ -x "$candidate" ]]; then
    nologin_shell="$candidate"
    break
  fi
done

if [[ -z "$nologin_shell" ]]; then
  echo "error: could not find a nologin shell" >&2
  exit 1
fi

if ! id -u "$service_user" >/dev/null 2>&1; then
  useradd \
    --system \
    --user-group \
    --home-dir "$home_dir" \
    --create-home \
    --shell "$nologin_shell" \
    --comment "Siren Driver service account" \
    "$service_user"
fi

passwd -l "$service_user" >/dev/null
usermod --shell "$nologin_shell" "$service_user"
usermod -a -G gpio "$service_user"

install -d -o "$service_user" -g "$service_user" -m 0750 "$home_dir"
install -d -o root -g "$service_user" -m 0750 "$config_dir"

env_file="$config_dir/siren-driver.env"
if [[ ! -f "$env_file" && -f .env.example ]]; then
  install -o root -g "$service_user" -m 0640 .env.example "$env_file"
fi

echo "Service user ready: $service_user"
echo "- login shell: $nologin_shell"
echo "- supplementary groups: $(id -nG "$service_user")"
echo "- home directory: $home_dir"
echo "- config directory: $config_dir"
echo "- env file: $env_file"
echo
echo "This creates a locked service account, not a full jail."
echo "Use a dedicated systemd unit with additional hardening for stronger isolation."
