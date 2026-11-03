#!/usr/bin/env bash
# Check live state, not the active flag of a completed oneshot.
set -euo pipefail
mode=${1:-}; component=${2:-}
[[ "$mode" == --check || "$mode" == --apply ]] || exit 2
state=/var/lib/tjikup/tailnet-services

# Operational probe errors must never be mistaken for configuration drift.
probe() { "$@" || return 2; }
predicate() {
    local result
    if jq -e "$@" >/dev/null; then return 0; else result=$?; fi
    [[ "$result" == 1 ]] && return 1
    return 2
}
enabled() {
    local value
    value=$(probe systemctl show --property=UnitFileState --value "$1") || return 2
    [[ "$value" == enabled ]]
}
active() {
    local value
    value=$(probe systemctl show --property=ActiveState --value "$1") || return 2
    [[ "$value" == active ]]
}
loaded() {
    local value
    value=$(probe systemctl show --property=NeedDaemonReload --value "$1") || return 2
    [[ "$value" == no ]]
}
unit_digest() { probe systemctl cat "$1" | sha256sum; }
policy_digest() {
    local tables rules
    tables=$(probe nft -j list tables) || return 2
    predicate '.nftables | any(.table.family == "inet" and .table.name == "tailnet_mullvad")' <<< "$tables" || return $?
    rules=$(probe nft -j list table inet tailnet_mullvad) || return 2
    # Packet counters and allocated handles change without policy drift.
    { sha256sum /etc/tailnet-mullvad.nft || return 2
      jq -cS 'del(.nftables[] | select(has("metainfo"))) |
        walk(if type == "object" then del(.handle) |
          if has("counter") then .counter |= del(.packets, .bytes) else . end
        else . end)' <<< "$rules" || return 2
    } | sha256sum
}
routing_check() {
    local family destination rules digest
    enabled tailnet-mullvad.service || return $?
    active tailnet-mullvad.service || return $?
    loaded tailnet-mullvad.service || return $?
    digest=$(unit_digest tailnet-mullvad.service) || return 2
    [[ -f "$state/routing" && "$(cat "$state/routing")" == "$digest" ]] || return 1
    for family in 4 6; do
        destination=100.64.0.0/10
        [[ "$family" == 4 ]] || destination=fd7a:115c:a1e0::/48
        rules=$(probe ip -j -"$family" rule show) || return 2
        predicate --arg dst "$destination" '
          [.[] | select(.dst == $dst and (.table | tostring) == "52") |
            select(.priority == 5100 or .priority == 5180 or .priority == 5197 or .priority == 5200)] |
          length == 1 and .[0].priority == 5100' <<< "$rules" || return $?
    done
}
dns_value() {
    local value
    value=$(probe resolvectl "$1" tailscale0) || return 2
    printf '%s\n' "${value#*): }"
}
check() {
    local digest value
    case "$component" in
        policy)
            digest=$(policy_digest) || return $?
            [[ -f "$state/policy" && "$(cat "$state/policy")" == "$digest" ]] ;;
        routing) routing_check ;;
        dns)
            enabled tailnet-dns.service || return $?
            loaded tailnet-dns.service || return $?
            value=$(dns_value dns) || return 2
            [[ "$value" == 100.85.220.100 ]] || return 1
            value=$(dns_value domain) || return 2
            [[ "$value" == '~tailb49776.ts.net tjik.internal' || "$value" == 'tjik.internal ~tailb49776.ts.net' ]] || return 1
            value=$(dns_value default-route) || return 2
            [[ "$value" == no ]] ;;
        timer)
            enabled tailnet-dns.timer || return $?
            loaded tailnet-dns.timer || return $?
            active tailnet-dns.timer ;;
        *) return 2 ;;
    esac
}
if check; then exit 0; else result=$?; fi
[[ "$mode" == --apply && "$result" == 1 ]] || exit "$result"
# Only record state following a successful apply. These receipts include live
# policy, so missing rules and changes made outside Tjikup still cause repair.
case "$component" in
    policy)
        nft -f /etc/tailnet-mullvad.nft
        digest=$(policy_digest)
        install -d -m755 "$state"
        printf '%s\n' "$digest" > "$state/policy.pending"
        mv "$state/policy.pending" "$state/policy" ;;
    routing)
        if loaded tailnet-mullvad.service; then :; else
            result=$?; [[ "$result" == 1 ]] || exit "$result"
            systemctl daemon-reload
        fi
        systemctl enable tailnet-mullvad.service
        systemctl restart tailnet-mullvad.service
        digest=$(unit_digest tailnet-mullvad.service)
        install -d -m755 "$state"
        printf '%s\n' "$digest" > "$state/routing.pending"
        mv "$state/routing.pending" "$state/routing" ;;
    dns|timer)
        unit=tailnet-dns.service
        [[ "$component" == dns ]] || unit=tailnet-dns.timer
        if loaded "$unit"; then :; else
            result=$?; [[ "$result" == 1 ]] || exit "$result"
            systemctl daemon-reload
        fi
        systemctl enable "$unit"
        systemctl restart "$unit" ;;
esac
check
