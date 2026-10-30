#!/usr/bin/env bash
# Scoped Si deployment; configuration is owned by the native file engine.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(hostname -s)" == si ]] || { echo 'Tasktjik authority runs only on Si' >&2; exit 1; }
runner="${TJIKUP_BINARY:-$HOME/.local/bin/tjikup}"
source_binary="$HOME/.local/lib/tasktjik/tasktjik-api"
if [[ "${1:-}" == --check ]]; then
    sudo -n cmp -s "$source_binary" /usr/local/lib/tasktjik/tasktjik-api
    sudo -n "$runner" files check --manifest "$repo_dir/system/native/si/manifest.json" --state-dir /var/lib/tjikup/files --group tasktjik-api
    systemctl is-enabled --quiet tasktjik-api.service tasktjik-serve.service
    systemctl is-active --quiet tasktjik-api.service tasktjik-serve.service
    exit 0
fi
test -x "$source_binary"
sudo "$runner" files apply --manifest "$repo_dir/system/native/si/manifest.json" --state-dir /var/lib/tjikup/files --group tasktjik-api
sudo systemd-sysusers /etc/sysusers.d/tasktjik.conf
sudo install -d -m 755 /usr/local/lib/tasktjik
if ! sudo cmp -s "$source_binary" /usr/local/lib/tasktjik/tasktjik-api; then
    sudo install -m 755 "$source_binary" /usr/local/lib/tasktjik/tasktjik-api.new
    sudo mv /usr/local/lib/tasktjik/tasktjik-api.new /usr/local/lib/tasktjik/tasktjik-api
fi
sudo systemctl daemon-reload
sudo systemctl enable tasktjik-api.service tasktjik-serve.service
sudo systemctl restart tasktjik-api.service
sudo systemctl restart tasktjik-serve.service
