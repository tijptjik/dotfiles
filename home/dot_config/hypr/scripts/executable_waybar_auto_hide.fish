#!/usr/bin/env fish

# Toggle Waybar when the pointer reaches/leaves a screen edge. Hyprland reports
# monitor dimensions in physical pixels but cursor coordinates in logical pixels,
# so account for the output scale before comparing them.
argparse 's/side=' -- $argv; or exit 2
set -l side $_flag_side
set -q side[1]; or set side bottom

# With Waybar's "mode": "hide", a new bar starts hidden. Keep that state
# while it is absent so an off-edge check does not reveal it.
set -l hidden true

while true
    set -l cursor (hyprctl cursorpos -j 2>/dev/null | jq -r '[.x, .y] | @tsv' | string split \t)
    set -l monitor (hyprctl monitors -j 2>/dev/null | jq -r '.[0] | [.width, .height, .scale] | @tsv' | string split \t)

    if test (count $cursor) -ne 2; or test (count $monitor) -ne 3; or not command pgrep -x waybar >/dev/null
        set hidden true
        sleep 0.1
        continue
    end

    set -l x $cursor[1]
    set -l y $cursor[2]
    set -l width (math "$monitor[1] / $monitor[3]")
    set -l height (math "$monitor[2] / $monitor[3]")
    set -l at_edge 0

    switch $side
        case top
            test $y -le 2; and set at_edge 1
        case bottom
            test $y -ge (math "$height - 2"); and set at_edge 1
        case left
            test $x -le 2; and set at_edge 1
        case right
            test $x -ge (math "$width - 2"); and set at_edge 1
        case '*'
            echo "waybar_auto_hide: unsupported side '$side'" >&2
            exit 2
    end

    if test $at_edge -eq 1; and test "$hidden" = true
        command pkill -USR1 -x waybar
        set hidden false
    else if test $at_edge -eq 0; and test "$hidden" != true
        command pkill -USR1 -x waybar
        set hidden true
    end

    sleep 0.1
end
