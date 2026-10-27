#!/usr/bin/env bash
# Install the on-demand launcher from the shared Tooltjik source, on every host.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_dir/scripts/ensure-tooltjik.sh"
ensure_tooltjik apps/runtjik/scripts/build.sh
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Runtjik requires Python 3.11+"'
python3 "$repo_dir/scripts/cache-install.py" runtjik \
    --input "$tool_repo/apps/runtjik" --input "$repo_dir/scripts/cache-install.py" \
    --output "$HOME/.local/bin/runtjik" --output "$HOME/.local/lib/runtjik" \
    -- bash -c 'bash "$1/apps/runtjik/scripts/build.sh" && bash "$1/apps/runtjik/scripts/install.sh"' _ "$tool_repo"
"$HOME/.local/bin/runtjik" check
# No GUI or user service is started on the server. On desktops, retire only the
# launcher processes, preserving applications in the old Hamr service cgroup.
if command -v quickshell >/dev/null && systemctl --user --quiet is-active graphical-session.target; then
    for unit in hamr-gtk.service hamr-daemon.service runtjik-gtk.service runtjik-daemon.service; do
        if systemctl --user --quiet is-active "$unit"; then
            kill_mode="$(systemctl --user show "$unit" -p KillMode --value)"
            if [[ "$unit" == *-gtk.service && "$kill_mode" != process ]]; then
                echo "Preserving $unit: KillMode=$kill_mode could stop launched applications." >&2
                exit 1
            fi
            systemctl --user stop "$unit"
        fi
        if systemctl --user --quiet is-enabled "$unit" 2>/dev/null; then
            systemctl --user disable "$unit"
        fi
    done
fi
