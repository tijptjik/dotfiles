#!/usr/bin/env bash
set -euo pipefail
repo="${TJIKOS_REPO:-$HOME/code/tjikos}"
[[ -f "$repo/apps/synctjik/scripts/install.sh" ]] || { echo 'Update the tjikOS checkout to a release containing synctjik.' >&2; exit 1; }
missing=()
for dependency in rclone restic python3; do
    command -v "$dependency" >/dev/null || missing+=("$dependency")
done
if (( ${#missing[@]} )); then sudo dnf install -y "${missing[@]}"; fi
bash "$repo/apps/synctjik/scripts/install.sh"
