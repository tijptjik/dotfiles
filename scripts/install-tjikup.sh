#!/usr/bin/env bash
# Install this fleet's runner dependency without applying home or system config.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -c 'import sys; assert sys.version_info >= (3, 10), "tjikup requires Python 3.10+"'

if [[ ! -f "$HOME/.local/share/chezetc/scripts/tjikup-apply.py" ]]; then
    echo 'Initialize/update ~/.local/share/chezetc before installing the fleet workflow.' >&2
    exit 1
fi

tool_repo="${TOOLTJIK_REPO:-}"
if [[ -z "$tool_repo" ]]; then
    if [[ -d "$HOME/code/tooltjik/.git" ]]; then
        tool_repo="$HOME/code/tooltjik"
    else
        tool_repo="$HOME/.local/share/tooltjik"
    fi
fi
if [[ ! -d "$tool_repo/.git" ]]; then
    mkdir -p -- "$(dirname -- "$tool_repo")"
    git clone https://github.com/tijptjik/tooltjik.git "$tool_repo"
fi
if [[ ! -f "$tool_repo/apps/tjikup/scripts/install.sh" ]]; then
    echo "Update $tool_repo to a revision containing apps/tjikup." >&2
    exit 1
fi

# Existing source checkouts are deliberately not pulled by an apply hook.
bash "$tool_repo/apps/tjikup/scripts/install.sh"
"$HOME/.local/bin/tjikup" --config "$repo_dir/tjikup.json" --check
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/tjikup"
mkdir -p -- "$config_dir"
staging_dir="$(mktemp -d "$config_dir/.install.XXXXXX")"
trap 'rm -rf -- "$staging_dir"' EXIT
ln -s -- "$repo_dir/tjikup.json" "$staging_dir/config.json"
mv -Tf -- "$staging_dir/config.json" "$config_dir/config.json"
