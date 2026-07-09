#!/usr/bin/env fish
# Debug script to print all Hyprland socket2 events

echo "Listening to Hyprland socket2 events..."
echo "========================================"

socat -U - UNIX-CONNECT:"$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock" | while read -l line
    echo "[$line]"
end
