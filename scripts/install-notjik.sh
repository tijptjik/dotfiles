#!/usr/bin/env bash
# Provision the desktop notification app without pulling an existing checkout.
set -euo pipefail

tool_repo="${TOOLTJIK_REPO:-}"
if [[ -z "$tool_repo" ]]; then
    if [[ -d "$HOME/code/tooltjik/.git" ]]; then
        tool_repo="$HOME/code/tooltjik"
    else
        tool_repo="$HOME/.local/share/tooltjik"
    fi
fi
# The earlier tjikup install hook provisions the shared tooltjik checkout.
if [[ ! -f "$tool_repo/apps/notjik/scripts/build.sh" ]]; then
    echo "Update $tool_repo to a revision containing apps/notjik." >&2
    exit 1
fi
command -v quickshell >/dev/null
command -v python3 >/dev/null
(cd "$tool_repo/apps/notjik" && bash scripts/build.sh)
bash "$tool_repo/scripts/install.sh" notjik

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
