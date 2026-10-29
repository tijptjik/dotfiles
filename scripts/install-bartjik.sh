#!/usr/bin/env bash
# Provision Bartjik before retiring the previous desktop bar.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/ensure-tjikos.sh"
ensure_tjikos apps/bartjik/scripts/build.sh
command -v quickshell >/dev/null
command -v python3 >/dev/null
# The native file phase owns units when invoked by Tjikup.
"${TJIKUP_BINARY:-tjikup}" workflow --repo "$(dirname "$script_dir")" cache-install bartjik \
    --input "$tool_repo/apps/bartjik" --input "$tool_repo/scripts/install.sh" \
    --input "$script_dir/cache-install.py" --input "$script_dir/install-bartjik.sh" \
    --output "$HOME/.local/bin/bartjik" --output "$HOME/.local/bin/bartjikctl" \
    --output "$HOME/.local/lib/bartjik" \
    -- bash -c '(cd "$1/apps/bartjik" && bash scripts/build.sh) && bash "$1/scripts/install.sh" bartjik' _ "$tool_repo" "$script_dir"
if [[ "${TJIKUP_MANAGED_CONFIG:-0}" != 1 ]]; then
    install -m 644 "$script_dir/../native/home/files/.config/systemd/user/bartjik.service" "$HOME/.config/systemd/user/bartjik.service"
    bash "$(dirname -- "${BASH_SOURCE[0]}")/activate-bartjik.sh"
fi
