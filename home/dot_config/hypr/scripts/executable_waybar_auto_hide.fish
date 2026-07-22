#!/usr/bin/env fish

# Show and hide Waybar when the pointer reaches/leaves a screen edge. Hyprland
# reports monitor dimensions in physical pixels but cursor coordinates in logical
# pixels, so account for the output scale before comparing them.
argparse 's/side=' -- $argv; or exit 2
set -l side $_flag_side
set -q side[1]; or set side bottom
# The interaction zone is the bar height plus twice its vertical margin:
# 36px + (2 * 16px) for the current laptop Waybar configuration.
set -l safe_zone 68

# Waybar starts visible in this setup. Keep that state while it is absent so
# the first off-edge check hides a newly created bar.
set -l visible true

while true
    set -l cursor (hyprctl cursorpos -j 2>/dev/null | jq -r '[.x, .y] | @tsv' | string split \t)
    set -l monitor

    if test (count $cursor) -eq 2
        # Pick the monitor containing the cursor. Do not use monitor array
        # order: Hyprland may list a secondary output before the primary one.
        set monitor (hyprctl monitors -j 2>/dev/null | jq -r \
            --argjson cursor_x "$cursor[1]" \
            --argjson cursor_y "$cursor[2]" \
            '.[] | select(
                ($cursor_x >= .x) and
                ($cursor_x < (.x + (.width / .scale))) and
                ($cursor_y >= .y) and
                ($cursor_y < (.y + (.height / .scale)))
            ) | [.x, .y, .width, .height, .scale] | @tsv' | string split \t)
    end

    if test (count $cursor) -ne 2; or test (count $monitor) -ne 5; or not command pgrep -x waybar >/dev/null
        set visible true
        sleep 0.1
        continue
    end

    set -l x (math "$cursor[1] - $monitor[1]")
    set -l y (math "$cursor[2] - $monitor[2]")
    set -l width (math "$monitor[3] / $monitor[5]")
    set -l height (math "$monitor[4] / $monitor[5]")
    set -l at_reveal_edge 0
    set -l in_safe_zone 0

    switch $side
        case top
            test $y -le 2; and set at_reveal_edge 1
            test $y -le $safe_zone; and set in_safe_zone 1
        case bottom
            test $y -ge (math "$height - 2"); and set at_reveal_edge 1
            test $y -ge (math "$height - $safe_zone"); and set in_safe_zone 1
        case left
            test $x -le 2; and set at_reveal_edge 1
            test $x -le $safe_zone; and set in_safe_zone 1
        case right
            test $x -ge (math "$width - 2"); and set at_reveal_edge 1
            test $x -ge (math "$width - $safe_zone"); and set in_safe_zone 1
        case '*'
            echo "waybar_auto_hide: unsupported side '$side'" >&2
            exit 2
    end

    if test $at_reveal_edge -eq 1; and test "$visible" != true
        command pkill -USR2 -x waybar
        set visible true
    else if test $in_safe_zone -eq 0; and test "$visible" = true
        command pkill -USR1 -x waybar
        set visible false
    end

    sleep 0.1
end
