#!/usr/bin/env bash
# Provision the desktop notification app and its source checkout.
set -euo pipefail

source "$(dirname -- "${BASH_SOURCE[0]}")/ensure-tjikos.sh"
ensure_tjikos apps/notjik/scripts/build.sh
command -v quickshell >/dev/null
command -v python3 >/dev/null
python3 "$(dirname -- "${BASH_SOURCE[0]}")/cache-install.py" notjik \
    --input "$tool_repo/apps/notjik" --input "$tool_repo/scripts/install.sh" \
    --input "$(dirname -- "${BASH_SOURCE[0]}")/cache-install.py" \
    --output "$HOME/.local/bin/notjik" --output "$HOME/.local/bin/notjikctl" \
    --output "$HOME/.local/lib/notjik" \
    --output "$HOME/.config/systemd/user/notjik.service" \
    --output "$HOME/.config/systemd/user/notjik-telegram.service" \
    --output "${XDG_DATA_HOME:-$HOME/.local/share}/dbus-1/services/org.freedesktop.Notifications.service" \
    -- bash -c '(cd "$1/apps/notjik" && bash scripts/build.sh) && bash "$1/scripts/install.sh" notjik' _ "$tool_repo"

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
