#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_dir/scripts/ensure-tjikos.sh"
# Notification transport owns only its own binaries. Producers are updated by
# their normal workflows; never replace a running archive worker here.
ensure_tjikos apps/notjik-service/scripts/build.sh
bash "$tool_repo/apps/notjik-service/scripts/build.sh"
install -d -m755 "$HOME/.local/lib/notjik-service" "$HOME/.local/bin" "$HOME/.config/systemd/user"
install -m755 "$tool_repo/apps/notjik-service/dist/bin/notjik-api" "$HOME/.local/lib/notjik-service/.notjik-api.pending"
mv "$HOME/.local/lib/notjik-service/.notjik-api.pending" "$HOME/.local/lib/notjik-service/notjik-api"
install -m755 "$tool_repo/apps/notjik-service/dist/bin/notjik-sync" "$HOME/.local/bin/.notjik-sync.pending"
mv "$HOME/.local/bin/.notjik-sync.pending" "$HOME/.local/bin/notjik-sync"
install -m644 "$tool_repo/apps/notjik-service/systemd/notjik-sync.service" "$HOME/.config/systemd/user/notjik-sync.service"
if [[ "$(hostname -s)" == si ]]; then
    bash "$repo_dir/scripts/activate-notjik-api.sh"
    install -d -m755 "$HOME/.config/systemd/user/notjik-sync.service.d"
    printf '%s\n' '[Service]' 'ExecStart=' 'ExecStart=/usr/bin/sg notjik -c "%h/.local/bin/notjik-sync run"' > "$HOME/.config/systemd/user/notjik-sync.service.d/socket-group.conf"
fi
if [[ ! -f "$HOME/.config/notjik/sync.json" ]]; then
    kind=desktop; [[ "$(hostname -s)" != si ]] || kind=server
    if [[ "$kind" == server ]]; then
        sg notjik -c "$HOME/.local/bin/notjik-sync connect http://localhost si server /run/notjik/api.sock"
    else
        "$HOME/.local/bin/notjik-sync" connect https://si.tailb49776.ts.net/notjik "$(hostname -s)" "$kind"
    fi
fi
systemctl --user daemon-reload
systemctl --user enable --now notjik-sync.service
if [[ "$(hostname -s)" == si ]]; then
    "$HOME/.local/bin/tasktjik" enroll --notifications >/dev/null
    install -m644 "$tool_repo/apps/tasktjik/systemd/tasktjik.service" "$tool_repo/apps/tasktjik/systemd/tasktjik.timer" "$HOME/.config/systemd/user/"
    install -d -m755 "$HOME/.config/systemd/user/tasktjik.service.d"
    printf '%s\n' '[Service]' 'ExecStart=' 'ExecStart=/usr/bin/sg notjik -c "%h/.local/bin/tasktjik notify"' > "$HOME/.config/systemd/user/tasktjik.service.d/socket-group.conf"
    systemctl --user daemon-reload
    systemctl --user enable --now tasktjik.timer
fi
