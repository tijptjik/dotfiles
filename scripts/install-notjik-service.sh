#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_dir/scripts/ensure-tjikos.sh"
mode=${1:---apply}
[[ "$mode" == --check || "$mode" == --apply ]] || exit 2
tool_repo=${TJIKOS_REPO:-$HOME/code/tjikos}
receipt="$HOME/.local/lib/notjik-service/install.sha256"
api="$HOME/.local/lib/notjik-service/notjik-api"
sync="$HOME/.local/bin/notjik-sync"
unit="$HOME/.config/systemd/user/notjik-sync.service"
source_digest() {
    # Include both Rust crates and build inputs, including uncommitted sources.
    (cd "$tool_repo" && find apps/notjik-service packages/notjik-sync \
        -type d \( -name target -o -name dist -o -name __pycache__ \) -prune -o \
        -type f ! -name '*.pyc' -print0 | LC_ALL=C sort -z | xargs -0 -r sha256sum) | sha256sum
}
installed_digest() { sha256sum "$api" "$sync"; }
payload_current() {
    [[ -x "$api" && -x "$sync" && -f "$receipt" ]] || return 1
    local expected
    expected=$( { printf '%s\n' "$sources"; installed_digest; } ) || return 2
    [[ "$(cat "$receipt")" == "$expected" ]]
}
service_property() {
    local value
    value=$(systemctl --user show --property="$1" --value notjik-sync.service) || return 2
    [[ "$value" == "$2" ]]
}
check() {
    payload_current || return $?
    cmp -s "$tool_repo/apps/notjik-service/systemd/notjik-sync.service" "$unit" || return 1
    [[ -f "$HOME/.config/notjik/sync.json" ]] || return 1
    service_property NeedDaemonReload no || return $?
    service_property UnitFileState enabled || return $?
    service_property ActiveState active || return $?
    if [[ "$(hostname -s)" == si ]]; then
        [[ -f "$HOME/.config/systemd/user/notjik-sync.service.d/socket-group.conf" ]] || return 1
        cmp -s <(printf '%s\n' '[Service]' 'ExecStart=' 'ExecStart=/usr/bin/sg notjik -c "%h/.local/bin/notjik-sync run"') \
            "$HOME/.config/systemd/user/notjik-sync.service.d/socket-group.conf" || return 1
        bash "$repo_dir/scripts/activate-notjik-api.sh" --check || return $?
    fi
}
if [[ "$mode" == --apply ]]; then
    ensure_tjikos apps/notjik-service/scripts/build.sh
fi
[[ -f "$tool_repo/apps/notjik-service/scripts/build.sh" ]] || exit 1
sources=$(source_digest) || exit 2
if check; then exit 0; else result=$?; fi
[[ "$mode" == --apply && "$result" == 1 ]] || exit "$result"
# Notification transport owns only its own binaries. Never replace producers or
# interrupt pinned archive workers while repairing this service.
changed=0
if payload_current; then :; else
    result=$?; [[ "$result" == 1 ]] || exit "$result"
    bash "$tool_repo/apps/notjik-service/scripts/build.sh"
    [[ "$(source_digest)" == "$sources" ]] || { echo 'Notification sources changed during build; retry.' >&2; exit 2; }
    install -d -m755 "$HOME/.local/lib/notjik-service" "$HOME/.local/bin"
    for entry in "notjik-api:$api" "notjik-sync:$sync"; do
        name=${entry%%:*}; destination=${entry#*:}
        source_binary="$tool_repo/apps/notjik-service/dist/bin/$name"
        if ! cmp -s "$source_binary" "$destination" || [[ ! -x "$destination" ]]; then
            install -m755 "$source_binary" "$destination.pending"
            mv "$destination.pending" "$destination"
            changed=1
        fi
        cmp -s "$source_binary" "$destination"
    done
fi
install -d -m755 "$HOME/.config/systemd/user"
if ! cmp -s "$tool_repo/apps/notjik-service/systemd/notjik-sync.service" "$unit"; then
    install -m644 "$tool_repo/apps/notjik-service/systemd/notjik-sync.service" "$unit"
    changed=1
fi
if [[ "$(hostname -s)" == si ]]; then
    if bash "$repo_dir/scripts/activate-notjik-api.sh" --check; then :; else
        result=$?; [[ "$result" == 1 ]] || exit "$result"
        bash "$repo_dir/scripts/activate-notjik-api.sh"
    fi
    override="$HOME/.config/systemd/user/notjik-sync.service.d/socket-group.conf"
    desired='ExecStart=/usr/bin/sg notjik -c "%h/.local/bin/notjik-sync run"'
    if ! cmp -s <(printf '%s\n' '[Service]' 'ExecStart=' "$desired") "$override"; then
        install -d -m755 "$(dirname "$override")"
        printf '%s\n' '[Service]' 'ExecStart=' "$desired" > "$override"
        changed=1
    fi
fi
if [[ ! -f "$HOME/.config/notjik/sync.json" ]]; then
    if [[ "$(hostname -s)" == si ]]; then
        sg notjik -c "$sync connect http://localhost si server /run/notjik/api.sock"
    else
        "$sync" connect https://si.tailb49776.ts.net/notjik "$(hostname -s)" desktop
    fi
fi
if service_property NeedDaemonReload no; then reload=0; else
    result=$?; [[ "$result" == 1 ]] || exit "$result"; reload=1
fi
if [[ "$changed" == 1 || "$reload" == 1 ]]; then
    systemctl --user daemon-reload
    systemctl --user enable notjik-sync.service
    systemctl --user restart notjik-sync.service
else
    systemctl --user enable --now notjik-sync.service
fi
{ printf '%s\n' "$sources"; installed_digest; } > "$receipt.pending"
mv "$receipt.pending" "$receipt"
check
