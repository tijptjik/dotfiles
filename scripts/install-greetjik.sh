#!/usr/bin/env bash
# Build and install Greetjik from the shared tools repository.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/ensure-tjikos.sh"
ensure_tjikos apps/greetjik/scripts/build.sh
"${TJIKUP_BINARY:-tjikup}" workflow --repo "$(dirname -- "$(dirname -- "${BASH_SOURCE[0]}")")" cache-install greetjik \
    --input "$tool_repo/apps/greetjik" --input "$tool_repo/scripts/install.sh" \
    --input "$(dirname -- "${BASH_SOURCE[0]}")/cache-install.py" \
    --output "$HOME/.local/bin/greetjik" --output "$HOME/.local/share/licenses/greetjik" \
    -- bash -c 'bash "$1/apps/greetjik/scripts/build.sh" && bash "$1/scripts/install.sh" greetjik' _ "$tool_repo"
