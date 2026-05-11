#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
service_user="siren"
home_dir="/var/lib/siren-driver"
config_dir="/etc/siren-driver"
app_dir="/opt/siren-driver"
venv_dir="$home_dir/venv"
service_bin_dir="$home_dir/bin"
service_uv_bin="$service_bin_dir/uv"
unit_name="siren-driver.service"
unit_path="/etc/systemd/system/$unit_name"
python_version="3.11"

resolve_uv() {
  local candidate=""

  if candidate=$(command -v uv 2>/dev/null); then
    printf '%s\n' "$candidate"
    return 0
  fi

  if [[ -n "${SUDO_USER:-}" ]]; then
    for candidate in \
      "/home/${SUDO_USER}/.local/bin/uv" \
      "/Users/${SUDO_USER}/.local/bin/uv" \
      "/Users/${SUDO_USER}/.cargo/bin/uv"
    do
      if [[ -x "$candidate" ]]; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done
  fi

  for candidate in /opt/homebrew/bin/uv /usr/local/bin/uv /usr/bin/uv; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

usage() {
  cat <<'EOF'
Usage: scripts/systemd-install.sh [options]

Installs the siren driver as a hardened host systemd service running under a
dedicated non-login service account.

Options:
  --user <name>         Service user name (default: siren)
  --home <path>         Service state directory (default: /var/lib/siren-driver)
  --config-dir <path>   Config directory for env file (default: /etc/siren-driver)
  --app-dir <path>      App install directory (default: /opt/siren-driver)
  --python <version>    Python version for uv sync (default: 3.11)
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
    --python)
      python_version="${2:-}"
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
  echo "error: run this script as root (for example: sudo ./scripts/systemd-install.sh)" >&2
  exit 1
fi

if ! uv_bin=$(resolve_uv); then
  echo "error: uv is required but was not found in PATH" >&2
  exit 1
fi

venv_dir="$home_dir/venv"
service_bin_dir="$home_dir/bin"
service_uv_bin="$service_bin_dir/uv"

"$repo_root/scripts/setup-siren-user.sh" \
  --user "$service_user" \
  --home "$home_dir" \
  --config-dir "$config_dir"

install -d -o root -g root -m 0755 "$app_dir"
install -d -o "$service_user" -g "$service_user" -m 0750 "$service_bin_dir"
install -d -o "$service_user" -g "$service_user" -m 0750 "$venv_dir"
install -o "$service_user" -g "$service_user" -m 0755 "$uv_bin" "$service_uv_bin"

rm -rf "$app_dir/src"
install -d -o root -g root -m 0755 "$app_dir/src"
cp -a "$repo_root/src/." "$app_dir/src/"
chown -R root:root "$app_dir/src"
install -o root -g root -m 0644 "$repo_root/pyproject.toml" "$app_dir/pyproject.toml"
install -o root -g root -m 0644 "$repo_root/uv.lock" "$app_dir/uv.lock"
if [[ -f "$repo_root/README.md" ]]; then
  install -o root -g root -m 0644 "$repo_root/README.md" "$app_dir/README.md"
fi

runuser -u "$service_user" -- env UV_PROJECT_ENVIRONMENT="$venv_dir" \
  bash -lc "cd '$app_dir' && '$service_uv_bin' sync --python '$python_version' --frozen --no-dev --no-install-project --extra pi"

sed \
  -e "s|{{SERVICE_USER}}|$service_user|g" \
  -e "s|{{APP_DIR}}|$app_dir|g" \
  -e "s|{{ENV_FILE}}|$config_dir/siren-driver.env|g" \
  -e "s|{{VENV_DIR}}|$venv_dir|g" \
  -e "s|{{HOME_DIR}}|$home_dir|g" \
  -e "s|{{CONFIG_DIR}}|$config_dir|g" \
  "$repo_root/deploy/systemd/siren-driver.service" > "$unit_path"

chmod 0644 "$unit_path"
systemctl daemon-reload
systemctl enable --now "$unit_name"

echo "Installed $unit_name"
echo "- app dir: $app_dir"
echo "- uv binary: $service_uv_bin"
echo "- venv dir: $venv_dir"
echo "- env file: $config_dir/siren-driver.env"
echo
echo "Check status with: systemctl status $unit_name --no-pager"
