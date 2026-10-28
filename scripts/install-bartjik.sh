#!/usr/bin/env bash
# Provision Bartjik before retiring the previous desktop bar.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/ensure-tjikos.sh"
ensure_tjikos apps/bartjik/scripts/build.sh
command -v quickshell >/dev/null
command -v python3 >/dev/null
# Include the managed Fish wrapper in the cached deployment, so it is never
# overwritten by the upstream unit on an otherwise unchanged installation.
python3 "$script_dir/cache-install.py" bartjik \
    --input "$tool_repo/apps/bartjik" --input "$tool_repo/scripts/install.sh" \
    --input "$script_dir/cache-install.py" --input "$script_dir/install-bartjik.sh" \
    --input "$script_dir/../native/home/files/.config/systemd/user/bartjik.service" \
    --output "$HOME/.local/bin/bartjik" --output "$HOME/.local/bin/bartjikctl" \
    --output "$HOME/.local/lib/bartjik" \
    --output "$HOME/.config/systemd/user/bartjik.service" \
    -- bash -c '(cd "$1/apps/bartjik" && bash scripts/build.sh) && bash "$1/scripts/install.sh" bartjik && install -m 644 "$2/../native/home/files/.config/systemd/user/bartjik.service" "$HOME/.config/systemd/user/bartjik.service"' _ "$tool_repo" "$script_dir"
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
