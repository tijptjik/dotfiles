#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# A check is read-only: activation is needed only for missing service state
# or unfinished migration, not on every configuration run.
if [[ "${1:-}" == --check ]]; then
    systemctl --user --quiet is-enabled bartjik.service || exit 1
    [[ "$(systemctl --user is-enabled waybar.service 2>/dev/null || true)" == masked ]] || exit 1
    if systemctl --user --quiet is-active waybar.service; then
        exit 1
    fi
    if systemctl --user --quiet is-active graphical-session.target; then
        systemctl --user --quiet is-active bartjik.service || exit 1
    fi
    [[ "$(systemctl --user show bartjik.service --property=NeedDaemonReload --value)" != yes ]] || exit 1
    for old in .config/waybar .config/quickshell/network .config/quickshell/audio .local/bin/waybar .local/lib/chezetc/waybar; do
        [[ ! -e "$HOME/$old" && ! -L "$HOME/$old" ]] || exit 1
    done
    if pgrep -u "$(id -u)" -x waybar >/dev/null; then
        exit 1
    fi
    exit 0
fi
systemctl --user daemon-reload
systemctl --user enable bartjik.service
if systemctl --user --quiet is-active graphical-session.target; then
    systemctl --user start bartjik.service
    systemctl --user --quiet is-active bartjik.service
fi
systemctl --user mask --now waybar.service
# Also retire bars launched directly by the old compositor configuration.
pkill -u "$(id -u)" -x waybar || test "$?" -eq 1
for panel in network audio; do
    quickshell kill --path "$HOME/.config/quickshell/$panel" 2>/dev/null || true
done
archive_root="${XDG_STATE_HOME:-$HOME/.local/state}/bartjik/migration"
for old in .config/waybar .config/quickshell/network .config/quickshell/audio .local/bin/waybar .local/lib/chezetc/waybar; do
    if [[ -e "$HOME/$old" || -L "$HOME/$old" ]]; then
        mkdir -p -- "$archive_root"
        archive_dir="$(mktemp -d "$archive_root/waybar.XXXXXXXX")"
        mv -- "$HOME/$old" "$archive_dir/$(basename -- "$old")"
    fi
done
