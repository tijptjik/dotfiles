#!/usr/bin/env fish

set mon_2_win_h_ratio 1.33
set win_ratio 1.66

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
if string match -qr -- 'zen|kitty' "$active_class"
    set monitor_height (hyprctl monitors -j | jq -r '.[] | select(.focused == true) | .height')
    set window_height (echo "$monitor_height / $mon_2_win_h_ratio" | bc | cut -d'.' -f1)
    set window_width (echo "$window_height * $win_ratio" | bc | cut -d'.' -f1)

    hyprctl dispatch togglefloating
    hyprctl dispatch resizeactive exact $window_width $window_height
    hyprctl dispatch centerwindow
else
    hyprctl dispatch togglefloating
end
