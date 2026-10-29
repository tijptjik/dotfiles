#!/usr/bin/env bash
# Install this fleet's runner dependency without applying home or system config.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

if [[ ! -f "$repo_dir/system/tjikup/recipes.json" ]]; then
    echo 'Initialize/update the system/ directory in the dotfiles checkout before installing the fleet workflow.' >&2
    exit 1
fi

source "$repo_dir/scripts/ensure-tjikos.sh"
ensure_tjikos apps/tjikup/scripts/install.sh

# Reject stale checkouts before replacing a working executable or cache record.
bash "$tool_repo/apps/tjikup/scripts/fetch-release.sh"
compatible_runner() {
    "$1" capabilities 2>/dev/null | jq -e '.native_workflow >= 1 and .bootstrap_archives >= 1 and .native_commands >= 1 and .native_installers >= 1 and .native_maintenance >= 1' >/dev/null  &&
        "$1" --config "$repo_dir/tjikup.json" --check >/dev/null 2>&1
}
if ! compatible_runner "$tool_repo/apps/tjikup/dist/tjikup"; then
    # A local migration can require features newer than the pinned release.
    # Keep a proven-compatible installed runner; never downgrade it or record
    # an install-cache success for a release that was not installed.
    installed_runner="$HOME/.local/bin/tjikup"
    if [[ -x "$installed_runner" ]] && compatible_runner "$installed_runner"; then
        printf '%s\n' 'SKIP    ✓ Tjikup    awaiting compatible release; installed runner retained' \
            '__stage_verb__:SKIP' '__stage_note__:awaiting compatible release'
        exit 0
    fi
    echo 'Pinned Tjikup release cannot validate this workflow, and no compatible installed runner is available. Existing files were preserved; update the release pin.' >&2
    exit 1
fi

"$tool_repo/apps/tjikup/dist/tjikup" workflow --repo "$repo_dir" cache-install tjikup \
    --input "$tool_repo/apps/tjikup" --input "$tool_repo/apps/tjikos-sh/release.json" --input "$tool_repo/apps/tjikup/src/workflow_services.rs" \
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
