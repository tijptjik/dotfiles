#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(hostname -s)" == si ]] || { echo 'Notjik authority runs only on Si' >&2; exit 1; }
runner="${TJIKUP_BINARY:-$HOME/.local/bin/tjikup}"
source_binary="$HOME/.local/lib/notjik-service/notjik-api"
if [[ "${1:-}" == --check ]]; then
    sudo -n cmp -s "$source_binary" /usr/local/lib/notjik/notjik-api
    sudo -n "$runner" files check --manifest "$repo_dir/system/native/si/manifest.json" --state-dir /var/lib/tjikup/files --group notjik-api
    systemctl is-active --quiet notjik-api.service notjik-serve.service notjik-system-sync.service
    exit 0
fi
test -x "$source_binary"
sudo "$runner" files apply --manifest "$repo_dir/system/native/si/manifest.json" --state-dir /var/lib/tjikup/files --group notjik-api
sudo systemd-sysusers /etc/sysusers.d/notjik.conf
sudo install -d -m755 /usr/local/lib/notjik
sudo install -m755 "$source_binary" /usr/local/lib/notjik/.notjik-api.pending
sudo mv /usr/local/lib/notjik/.notjik-api.pending /usr/local/lib/notjik/notjik-api
sudo install -m755 "$HOME/.local/bin/notjik-sync" /usr/local/bin/.notjik-sync.pending
sudo mv /usr/local/bin/.notjik-sync.pending /usr/local/bin/notjik-sync
sudo systemctl daemon-reload
sudo systemctl enable notjik-api.service notjik-serve.service
sudo systemctl restart notjik-api.service notjik-serve.service
if ! sudo test -f /etc/notjik/system-client.json; then
    sudo env NOTJIK_SYNC_CONFIG=/etc/notjik/system-client.json NOTJIK_SYNC_STATE=/var/lib/notjik-system-client /usr/local/bin/notjik-sync connect http://localhost si-system server /run/notjik/api.sock
fi
sudo systemctl enable --now notjik-system-sync.service
