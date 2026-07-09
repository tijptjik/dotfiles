#!/usr/bin/env fish

# --- CONFIG ---
set TARGET_MONITOR "DP-1"
set SPECIAL_WS "chat"

if test -n "$argv[1]"; and string match -qr '^[[:alnum:]_-]+$' -- "$argv[1]"
    set SPECIAL_WS "$argv[1]"
end

set CURRENT_WIN (hyprctl activewindow -j | jq -r '.address')
set CURRENT_MON (hyprctl monitors -j | jq -r '.[] | select(.focused) | .name')

if test "$CURRENT_MON" = "$TARGET_MONITOR"
    hyprctl dispatch togglespecialworkspace "$SPECIAL_WS"
    exit 0
end

hyprctl keyword cursor:no_warps true > /dev/null
hyprctl --batch "dispatch focusmonitor $TARGET_MONITOR ; dispatch togglespecialworkspace $SPECIAL_WS ; dispatch focuswindow address:$CURRENT_WIN"
hyprctl keyword cursor:no_warps false > /dev/null
