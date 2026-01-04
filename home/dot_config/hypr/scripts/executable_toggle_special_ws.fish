#!/usr/bin/env fish

# --- CONFIG ---
set TARGET_MONITOR "HDMI-A-1"
set SPECIAL_WS "chat"

set CURRENT_WIN (hyprctl activewindow -j | jq -r '.address')
set CURRENT_MON (hyprctl monitors -j | jq -r '.[] | select(.focused) | .name')

echo $CURRENT_WIN
echo $CURRENT_MON

if test "$CURRENT_MON" = "$TARGET_MONITOR"
    hyprctl dispatch togglespecialworkspace "$SPECIAL_WS"
    exit 0
end


hyprctl keyword cursor:no_warps true > /dev/null

hyprctl --batch "dispatch focusmonitor $TARGET_MONITOR ; dispatch togglespecialworkspace $SPECIAL_WS ; dispatch focuswindow address:$CURRENT_WIN"

hyprctl keyword cursor:no_warps false > /dev/null
