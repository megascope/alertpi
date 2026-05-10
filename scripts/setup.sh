#!/usr/bin/env bash
set -euo pipefail

python_version="3.11"
include_dev=true
force_pi="auto"

usage() {
  cat <<'EOF'
Usage: scripts/setup.sh [options]

Options:
  --python <version>  Python version to use with uv (default: 3.11)
  --pi                Force install of Raspberry Pi GPIO extra
  --no-pi             Skip Raspberry Pi GPIO extra
  --no-dev            Skip dev dependencies
  -h, --help          Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      python_version="${2:-}"
      if [[ -z "$python_version" ]]; then
        echo "error: --python requires a version" >&2
        exit 2
      fi
      shift 2
      ;;
    --pi)
      force_pi="yes"
      shift
      ;;
    --no-pi)
      force_pi="no"
      shift
      ;;
    --no-dev)
      include_dev=false
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

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but was not found in PATH." >&2
  echo "Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

os="$(uname -s | tr '[:upper:]' '[:lower:]')"
arch="$(uname -m)"

is_pi=false
if [[ "$force_pi" == "yes" ]]; then
  is_pi=true
elif [[ "$force_pi" == "auto" && "$os" == "linux" && ( "$arch" == "armv7l" || "$arch" == "aarch64" ) ]]; then
  is_pi=true
fi

extras=()
if [[ "$include_dev" == true ]]; then
  extras+=(--extra dev)
fi
if [[ "$is_pi" == true ]]; then
  extras+=(--extra pi)
fi

echo "Installing Python ${python_version} via uv (if needed)..."
uv python install "$python_version"

echo "Syncing dependencies into .venv..."
uv sync --python "$python_version" "${extras[@]}"

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Setup complete."
echo "- Python: ${python_version}"
echo "- Extras: ${extras[*]:-(none)}"
