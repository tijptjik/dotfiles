#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_dir/scripts/ensure-tjikos.sh"
ensure_tjikos apps/tasktjik/scripts/build.sh
# Older pinned runners predate the Tasktjik cache key. Use the same install
# commands directly until that capability reaches the pinned release.
if ! "${TJIKUP_BINARY:-tjikup}" capabilities | jq -e '.tasktjik_install_cache >= 1' >/dev/null 2>&1; then
    bash "$tool_repo/apps/tasktjik/scripts/build.sh"
    bash "$tool_repo/apps/tasktjik/scripts/install.sh"
else
    "${TJIKUP_BINARY:-tjikup}" workflow --repo "$repo_dir" cache-install tasktjik \
        --input "$tool_repo/apps/tasktjik" --input "$tool_repo/docs/icons/tasktjik.svg" \
        --output "$HOME/.local/bin/tasktjik" --output "$HOME/.local/lib/tasktjik" \
        --output "$HOME/.local/share/applications/tasktjik.desktop" \
        --output "$HOME/.local/share/icons/hicolor/scalable/apps/tasktjik.svg" \
        -- bash -c 'bash "$1/apps/tasktjik/scripts/build.sh" && bash "$1/apps/tasktjik/scripts/install.sh"' _ "$tool_repo"
fi

# Service configuration precedes package updates. Enroll reminders only after
# this installer has deployed the current producer, including on cache hits.
# A fresh install reaches this again in the update phase after Notjik is ready.
if [[ "$(hostname -s)" == si && -f "$HOME/.config/notjik/sync.json" ]]; then
    "$HOME/.local/bin/tasktjik" enroll --notifications >/dev/null
    install -m644 "$tool_repo/apps/tasktjik/systemd/tasktjik.service" "$tool_repo/apps/tasktjik/systemd/tasktjik.timer" "$HOME/.config/systemd/user/"
    install -d -m755 "$HOME/.config/systemd/user/tasktjik.service.d"
    printf '%s\n' '[Service]' 'ExecStart=' 'ExecStart=/usr/bin/sg tasktjik -c "sg notjik -c \"%h/.local/bin/tasktjik notify\""' > "$HOME/.config/systemd/user/tasktjik.service.d/socket-group.conf"
    systemctl --user daemon-reload
    systemctl --user enable --now tasktjik.timer
fi
