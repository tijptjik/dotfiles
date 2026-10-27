#!/usr/bin/env bash
# Install this fleet's runner dependency without applying home or system config.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -c 'import sys; assert sys.version_info >= (3, 10), "tjikup requires Python 3.10+"'

if [[ ! -f "$HOME/.local/share/chezetc/scripts/tjikup-apply.py" ]]; then
    echo 'Initialize/update ~/.local/share/chezetc before installing the fleet workflow.' >&2
    exit 1
fi

source "$repo_dir/scripts/ensure-tooltjik.sh"
ensure_tooltjik apps/tjikup/scripts/install.sh

python3 "$repo_dir/scripts/cache-install.py" tjikup \
    --input "$tool_repo/apps/tjikup" --input "$repo_dir/scripts/cache-install.py" \
    --output "$HOME/.local/bin/tjikup" --output "$HOME/.local/share/icons/tjikup.png" \
    --output "$HOME/.local/share/icons/hicolor/256x256/apps/tjikup-notification.png" \
    -- bash "$tool_repo/apps/tjikup/scripts/install.sh"
"$HOME/.local/bin/tjikup" --config "$repo_dir/tjikup.json" --check
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/tjikup"
mkdir -p -- "$config_dir"
staging_dir="$(mktemp -d "$config_dir/.install.XXXXXX")"
trap 'rm -rf -- "$staging_dir"' EXIT
ln -s -- "$repo_dir/tjikup.json" "$staging_dir/config.json"
mv -Tf -- "$staging_dir/config.json" "$config_dir/config.json"
