#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_dir/scripts/ensure-tjikos.sh"
ensure_tjikos apps/tasktjik/scripts/build.sh
# Older pinned runners predate the Tasktjik cache key. Use the same install
# commands directly until that capability reaches the pinned release.
if ! "${TJIKUP_BINARY:-tjikup}" capabilities | jq -e '.tasktjik_install_cache >= 1' >/dev/null 2>&1; then
    bash "$tool_repo/apps/tasktjik/scripts/build.sh"
    bash "$tool_repo/apps/tasktjik/scripts/install.sh"
    exit 0
fi
"${TJIKUP_BINARY:-tjikup}" workflow --repo "$repo_dir" cache-install tasktjik \
    --input "$tool_repo/apps/tasktjik" --input "$tool_repo/docs/icons/tasktjik.svg" \
    --output "$HOME/.local/bin/tasktjik" --output "$HOME/.local/lib/tasktjik" \
    --output "$HOME/.local/share/applications/tasktjik.desktop" \
    --output "$HOME/.local/share/icons/hicolor/scalable/apps/tasktjik.svg" \
    -- bash -c 'bash "$1/apps/tasktjik/scripts/build.sh" && bash "$1/apps/tasktjik/scripts/install.sh"' _ "$tool_repo"
