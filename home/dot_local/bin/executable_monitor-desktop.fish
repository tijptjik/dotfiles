#!/usr/bin/env fish

# Switch to Desktop monitor profile

# Set monitors for desktop use
# DP-1: Main ultrawide
# DP-2: Side monitor
# HDMI-A-1: TV (disabled)
hyprctl --batch "\
    keyword monitor DP-1,3440x1440@119.960999,0x0,auto,vrr,1;\
    keyword monitor DP-2,1920x1080@74.97,3440x720,auto,vrr,1;\
    keyword monitor HDMI-A-1,disable"

# Restore default hypridle configuration by removing any overrides
set override_dir (path expand ~/.config/systemd/user/hypridle.service.d)
if test -d $override_dir
    rm -rf $override_dir
end

# Reload systemd and restart hypridle
systemctl --user daemon-reload
systemctl --user restart hypridle.service

echo "Switched to Desktop monitor profile."
