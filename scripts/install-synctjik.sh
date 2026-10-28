#!/usr/bin/env bash
set -euo pipefail
repo="${TJIKOS_REPO:-$HOME/code/tjikos}"
[[ -f "$repo/apps/synctjik/scripts/install.sh" ]] || { echo 'Update the tjikOS checkout to a release containing synctjik.' >&2; exit 1; }
command -v rclone >/dev/null || sudo dnf install -y rclone
bash "$repo/apps/synctjik/scripts/install.sh"
