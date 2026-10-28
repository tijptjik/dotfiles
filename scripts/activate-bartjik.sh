#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
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
