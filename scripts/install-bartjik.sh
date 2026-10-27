#!/usr/bin/env bash
# Provision Bartjik before retiring the previous desktop bar.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/ensure-tjikos.sh"
ensure_tjikos apps/bartjik/scripts/build.sh
command -v quickshell >/dev/null
command -v python3 >/dev/null
(cd "$tool_repo/apps/bartjik" && bash scripts/build.sh)
bash "$tool_repo/scripts/install.sh" bartjik
# Preserve the managed Fish environment wrapper over the upstream unit.
install -m 644 "$(dirname -- "${BASH_SOURCE[0]}")/../home/dot_config/systemd/user/bartjik.service" "$HOME/.config/systemd/user/bartjik.service"
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
