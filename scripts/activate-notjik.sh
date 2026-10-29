#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# A check is read-only: activation is needed only for missing service state
# or unfinished migration, not on every configuration run.
if [[ "${1:-}" == --check ]]; then
    systemctl --user --quiet is-enabled notjik.service || exit 1
    [[ "$(systemctl --user is-enabled dunst.service 2>/dev/null || true)" == masked ]] || exit 1
    if systemctl --user --quiet is-active dunst.service; then
        exit 1
    fi
    if systemctl --user --quiet is-active graphical-session.target; then
        systemctl --user --quiet is-active notjik.service || exit 1
    fi
    [[ "$(systemctl --user show notjik.service --property=NeedDaemonReload --value)" != yes ]] || exit 1
    for old in .config/dunst; do
        [[ ! -e "$HOME/$old" && ! -L "$HOME/$old" ]] || exit 1
    done
    exit 0
fi
# Retire the old server only after its replacement installed successfully.
# Masking also prevents a packaged unit from being enabled again at login.
systemctl --user daemon-reload
systemctl --user mask --now dunst.service
if [[ -e "$HOME/.config/dunst" || -L "$HOME/.config/dunst" ]]; then
    archive_root="${XDG_STATE_HOME:-$HOME/.local/state}/notjik/migration"
    mkdir -p -- "$archive_root"
    archive_dir="$(mktemp -d "$archive_root/dunst.XXXXXXXX")"
    mv -- "$HOME/.config/dunst" "$archive_dir/config"
fi
systemctl --user enable notjik.service
# Do not launch a graphical service during headless provisioning, or restart
# an active Notjik session that may hold unsent replies and recordings.
if systemctl --user --quiet is-active graphical-session.target; then
    systemctl --user start notjik.service
fi
