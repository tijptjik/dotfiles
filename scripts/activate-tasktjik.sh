#!/usr/bin/env bash
# Client-only reminder migration; no authority data or archive worker changes.
set -euo pipefail
if [[ "${1:-}" == --check ]]; then
    systemctl --user is-enabled --quiet tasktjik.timer || exit 1
    systemctl --user is-active --quiet tasktjik.timer || exit 1
    if systemctl --user is-enabled --quiet runtjik-todo.timer 2>/dev/null; then exit 1; fi
    if systemctl --user is-active --quiet runtjik-todo.timer 2>/dev/null; then exit 1; fi
    exit 0
fi
test -x "$HOME/.local/bin/tasktjik"
test -f "${XDG_CONFIG_HOME:-$HOME/.config}/tasktjik/tasktjik.conf"
systemctl --user daemon-reload
if systemctl --user cat runtjik-todo.timer >/dev/null 2>&1; then
    systemctl --user disable --now runtjik-todo.timer
fi
systemctl --user enable --now tasktjik.timer
