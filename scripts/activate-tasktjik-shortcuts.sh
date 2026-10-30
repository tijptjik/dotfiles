#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(hostname -s)" == si ]] || exit 1
runner="${TJIKUP_BINARY:-$HOME/.local/bin/tjikup}"
if [[ "${1:-}" == --check ]]; then
    sudo -n "$runner" files check --manifest "$repo_dir/system/native/si/manifest.json" --state-dir /var/lib/tjikup/files --group tasktjik-shortcuts
    for unit in tasktjik-dns.service tasktjik-shortcuts.service; do
        systemctl is-enabled --quiet "$unit"
        systemctl is-active --quiet "$unit"
    done
    exit 0
fi
sudo "$runner" files apply --manifest "$repo_dir/system/native/si/manifest.json" --state-dir /var/lib/tjikup/files --group tasktjik-shortcuts
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
sudo systemctl daemon-reload
sudo systemctl enable tasktjik-dns.service tasktjik-shortcuts.service
sudo systemctl restart tasktjik-dns.service tasktjik-shortcuts.service
