#!/bin/bash
# ~/.config/hypr/scripts/tile_zen_windows.sh

# Window dimensions
WINDOW_WIDTH=500
WINDOW_HEIGHT=889
SPACING=24
MAX_WINDOWS=6

# Screen dimensions (3440x1440 at 0x0)
SCREEN_WIDTH=3440
SCREEN_HEIGHT=1440
SCREEN_X=0
SCREEN_Y=0

# Get all window addresses on current workspace matching the title
WINDOWS=$(hyprctl clients -j | jq -r --arg title "HYPE.HK — Zen Browser" '
    [.[] | select(.workspace.id == '"$(hyprctl activeworkspace -j | jq '.id')"' and .title == $title)] | map(.address) | .[]
')

# Convert to array
readarray -t WINDOW_ARRAY <<< "$WINDOWS"

# Count windows
NUM_WINDOWS=${#WINDOW_ARRAY[@]}

# Limit to MAX_WINDOWS
if [ "$NUM_WINDOWS" -gt "$MAX_WINDOWS" ]; then
    NUM_WINDOWS=$MAX_WINDOWS
fi

# Calculate total width needed
TOTAL_WIDTH=$((NUM_WINDOWS * WINDOW_WIDTH + (NUM_WINDOWS - 1) * SPACING))

# Calculate starting positions (centered)
START_X=$((SCREEN_X + (SCREEN_WIDTH - TOTAL_WIDTH) / 2))
START_Y=$((SCREEN_Y + (SCREEN_HEIGHT - WINDOW_HEIGHT) / 2))

# Position each window
for ((i=0; i<NUM_WINDOWS; i++)); do
    ADDRESS=${WINDOW_ARRAY[$i]}
    X=$((START_X + i * (WINDOW_WIDTH + SPACING)))
    Y=$START_Y

    # Set floating and resize
    hyprctl dispatch setfloating address:$ADDRESS
    hyprctl dispatch resizewindowpixel exact $WINDOW_WIDTH $WINDOW_HEIGHT,address:$ADDRESS
    hyprctl dispatch movewindowpixel exact $X $Y,address:$ADDRESS
done
