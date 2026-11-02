#!/usr/bin/env bash
# Build incrementally, then install only when the root-owned module differs.
set -euo pipefail
# System files depend on this check on every role, but only clients use oo7 PAM.
if [[ "${TJIKUP_ROLE:-}" == server ]]; then
    printf '%s\n' 'SKIP    - Hyprlock keyring    not used on servers'
    exit 0
fi
if [[ "${1:-}" == --check ]]; then
    tool_repo="${TJIKOS_REPO:-$HOME/code/tjikos}"
    exec bash "$tool_repo/apps/oo7-pam/scripts/install.sh" --check
fi
[[ $# == 0 ]] || { echo 'Usage: install-hyprlock-keyring.sh [--check]' >&2; exit 2; }
source "$(dirname -- "${BASH_SOURCE[0]}")/ensure-tjikos.sh"
ensure_tjikos apps/oo7-pam/scripts/build.sh
if ! command -v cargo >/dev/null 2>&1; then
    echo 'Install Rust/Cargo before enabling Hyprlock keyring integration.' >&2
    exit 1
fi
bash "$tool_repo/apps/oo7-pam/scripts/build.sh"
if bash "$tool_repo/apps/oo7-pam/scripts/install.sh" --check; then
    printf '%s\n' 'SKIP    ✓ Hyprlock keyring    no changes' '__stage_verb__:SKIP' '__stage_note__:no changes'
    exit 0
fi
bash "$tool_repo/apps/oo7-pam/scripts/install.sh"
printf '%s\n' 'CONFIG  ✓ Hyprlock keyring    module installed' '__stage_verb__:CONFIG' '__stage_note__:module installed'
