#!/usr/bin/env bash
# Configure client reminders without changing authority data or archive workers.
set -euo pipefail
if [[ "${1:-}" == --check ]]; then
    systemctl --user is-enabled --quiet tasktjik.timer || exit 1
    systemctl --user is-active --quiet tasktjik.timer || exit 1
    exit 0
fi
test -x "$HOME/.local/bin/tasktjik"
test -f "${XDG_CONFIG_HOME:-$HOME/.config}/tasktjik/tasktjik.conf"
"$HOME/.local/bin/tasktjik" connect https://si.tailb49776.ts.net/tasktjik --notifications
systemctl --user daemon-reload
systemctl --user enable --now tasktjik.timer
