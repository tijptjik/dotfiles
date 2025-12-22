#!/usr/bin/env fish

# Switch to Game monitor profile

# Set monitors for gaming
# DP-1: Main ultrawide (for audio passthrough)
# DP-2: Side monitor (disabled)
# HDMI-A-1: TV (main display for gaming)
hyprctl --batch "\
    keyword monitor DP-1,3440x1440@119.960999,0x0,auto,vrr,1;\
    keyword monitor DP-2,disable;\
    keyword monitor HDMI-A-1,3840x2160@60,auto"

# Override hypridle configuration for gaming
set override_dir (path expand ~/.config/systemd/user/hypridle.service.d)
set override_file $override_dir/override.conf
mkdir -p $override_dir
# Clear existing ExecStart and set the new one for game mode.
# The '%h' is interpreted by systemd as the user's home directory.
echo -e "[Service]\nExecStart=\nExecStart=hypridle -c %h/.config/hypr/hypridle_game.conf" > $override_file

# Reload systemd and restart hypridle
systemctl --user daemon-reload
systemctl --user restart hypridle.service

echo "Switched to Game monitor profile."
echo "Note: DP-1 will turn off after 15s via hypridle service."
