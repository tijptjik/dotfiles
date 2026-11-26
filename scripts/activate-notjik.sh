#!/usr/bin/env bash
set -euo pipefail
# Checks are read-only and converge only the current service.
if [[ "${1:-}" == --check ]]; then
    systemctl --user --quiet is-enabled notjik.service || exit 1
    if systemctl --user --quiet is-active graphical-session.target; then
        systemctl --user --quiet is-active notjik.service || exit 1
    fi
    [[ "$(systemctl --user show notjik.service --property=NeedDaemonReload --value)" != yes ]] || exit 1
    exit 0
fi
systemctl --user daemon-reload
systemctl --user enable notjik.service
# Start is idempotent; preserve active sessions and avoid headless launches.
if systemctl --user --quiet is-active graphical-session.target; then
    systemctl --user start notjik.service
    systemctl --user --quiet is-active notjik.service
fi
