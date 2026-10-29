#!/usr/bin/env bash
# Install the on-demand launcher from the shared tjikOS source, on every host.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_dir/scripts/ensure-tjikos.sh"
ensure_tjikos apps/runtjik/scripts/build.sh
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Runtjik requires Python 3.11+"'
"${TJIKUP_BINARY:-tjikup}" workflow --repo "$repo_dir" cache-install runtjik \
    --input "$tool_repo/apps/runtjik" --input "$repo_dir/scripts/cache-install.py" \
    --output "$HOME/.local/bin/runtjik" --output "$HOME/.local/lib/runtjik" \
    -- bash -c 'bash "$1/apps/runtjik/scripts/build.sh" && bash "$1/apps/runtjik/scripts/install.sh"' _ "$tool_repo"
if [[ "${TJIKUP_MANAGED_CONFIG:-0}" != 1 ]]; then
    bash "$(dirname -- "${BASH_SOURCE[0]}")/activate-runtjik.sh"
fi
