#!/usr/bin/env bash
# Build and install the native pony renderer from the shared tools repository.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/ensure-tooltjik.sh"
ensure_tooltjik apps/pony-rs/scripts/build.sh
python3 "$(dirname -- "${BASH_SOURCE[0]}")/cache-install.py" pony-rs \
    --input "$tool_repo/apps/pony-rs" --input "$tool_repo/scripts/install.sh" \
    --input "$(dirname -- "${BASH_SOURCE[0]}")/cache-install.py" \
    --output "$HOME/.local/bin/pony-rs" --output "$HOME/.local/share/licenses/pony-rs" \
    -- bash -c 'bash "$1/apps/pony-rs/scripts/build.sh" && bash "$1/scripts/install.sh" pony-rs' _ "$tool_repo"
