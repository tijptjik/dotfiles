#!/usr/bin/env fish

# Get the active window data as JSON
set active_window_data (hyprctl -j activewindow)

# Extract class and floating status
set active_class (echo "$active_window_data" | jq -r '.class')
set is_floating (echo "$active_window_data" | jq -r '.floating')

# If the window is already floating, toggle it back to tiled
if test "$is_floating" = "true"
    hyprctl dispatch togglefloating
    exit 0
end

# Resize and float the active window based on its class
if string match -q -- '*zen*|*kitty*' "$active_class"
    hyprctl dispatch togglefloating
    hyprctl dispatch resizeactive exact 1800 1200
    hyprctl dispatch centerwindow
else
    hyprctl dispatch togglefloating
end
