#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
check_only=0
case "${1:-}" in
    --check) check_only=1 ;;
    "") ;;
    *) echo "Usage: $0 [--check]" >&2; exit 2 ;;
esac
if (( check_only )); then
    python3 "$repo_dir/scripts/cleanup-launcher-entries.py" --check
else
    python3 "$repo_dir/scripts/cleanup-launcher-entries.py" --apply
fi
"$HOME/.local/bin/runtjik" check
# No GUI or user service is started on the server. On desktops, retire only the
# launcher processes, preserving applications in the old Hamr service cgroup.
if command -v quickshell >/dev/null && systemctl --user --quiet is-active graphical-session.target; then
    for unit in hamr-gtk.service hamr-daemon.service runtjik-gtk.service runtjik-daemon.service; do
        if systemctl --user --quiet is-active "$unit"; then
            (( check_only )) && exit 1
            kill_mode="$(systemctl --user show "$unit" -p KillMode --value)"
            if [[ "$unit" == *-gtk.service && "$kill_mode" != process ]]; then
                echo "Preserving $unit: KillMode=$kill_mode could stop launched applications." >&2
                exit 1
            fi
            systemctl --user stop "$unit"
        fi
        if systemctl --user --quiet is-enabled "$unit" 2>/dev/null; then
            (( check_only )) && exit 1
            systemctl --user disable "$unit"
        fi
    done
fi
