#!/usr/bin/env fish

function tailnet_state
    command tailscale status --json 2>/dev/null
end

if test "$argv[1]" = toggle
    set state (tailnet_state | command jq -r '.BackendState // "Unavailable"')
    if test "$state" = Running
        command tailscale down
    else
        command timeout 15s tailscale up
    end
    exit $status
end

# Material Symbols Rounded renders this VPN-lock ligature much more clearly
# than Tailscale's dense nine-dot brand mark at Waybar's small status size.
set icon 'vpn_lock'
set state inactive
set tooltip 'Tailscale disconnected'
set status_json (tailnet_state)
set backend (printf '%s' "$status_json" | command jq -r '.BackendState // "Unavailable"' 2>/dev/null)

if test "$backend" = Running
    set state active
    set tailnet_host (printf '%s' "$status_json" | command jq -r '.Self.DNSName // "connected"' 2>/dev/null | string trim --chars='.')
    set tooltip "Tailscale connected · $tailnet_host"
else if test "$backend" = NeedsLogin
    set tooltip 'Tailscale needs login'
else if test "$backend" = Unavailable
    set tooltip 'Tailscale unavailable'
end

printf '{"text":"%s","class":"%s","tooltip":"%s"}\n' "$icon" "$state" "$tooltip"
