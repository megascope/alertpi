#!/usr/bin/env bash
set -euo pipefail

unit_dir=${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd

systemctl --user disable --now siren-webhook.service || true
rm -f "$unit_dir/siren-webhook.container"
systemctl --user daemon-reload
