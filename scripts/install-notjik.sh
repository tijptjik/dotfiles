#!/usr/bin/env bash
# Provision the desktop notification app and its source checkout.
set -euo pipefail

source "$(dirname -- "${BASH_SOURCE[0]}")/ensure-tjikos.sh"
ensure_tjikos apps/notjik/scripts/build.sh
command -v quickshell >/dev/null
command -v python3 >/dev/null
"${TJIKUP_BINARY:-tjikup}" workflow --repo "$(dirname -- "$(dirname -- "${BASH_SOURCE[0]}")")" cache-install notjik \
    --input "$tool_repo/apps/notjik" --input "$tool_repo/scripts/install.sh" \
    --input "$(dirname -- "${BASH_SOURCE[0]}")/cache-install.py" \
    --output "$HOME/.local/bin/notjik" --output "$HOME/.local/bin/notjikctl" \
    --output "$HOME/.local/lib/notjik" \
    -- bash -c '(cd "$1/apps/notjik" && bash scripts/build.sh) && bash "$1/scripts/install.sh" notjik' _ "$tool_repo"

if [[ "${TJIKUP_MANAGED_CONFIG:-0}" != 1 ]]; then
    bash "$(dirname -- "${BASH_SOURCE[0]}")/activate-notjik.sh"
fi
