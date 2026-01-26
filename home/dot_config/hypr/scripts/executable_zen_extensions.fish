#!/usr/bin/env fish

set zen_json (dirname (status --current-filename))/zen_extensions.json

# Get primary monitor info once at startup (monitor 0 is always the primary)
set -g monitor_info (hyprctl monitors -j | jq '.[0]')
set -g screen_width (echo $monitor_info | jq -r '.width')
set -g screen_height (echo $monitor_info | jq -r '.height')
set -g monitor_x (echo $monitor_info | jq -r '.x')  # Monitor offset X
set -g monitor_y (echo $monitor_info | jq -r '.y')  # Monitor offset Y

function center_window
    set -l win_width $argv[1]
    set -l win_height $argv[2]

    # Calculate centered position relative to monitor: (screen_size - window_size) / 2
    set -l rel_x (math "floor(($screen_width - $win_width) / 2)")
    set -l rel_y (math "floor(($screen_height - $win_height) / 2)")

    # Add monitor offset to get absolute position
    set -l pos_x (math "$monitor_x + $rel_x")
    set -l pos_y (math "$monitor_y + $rel_y")

    # Clamp to ensure window stays on screen
    set -l max_x (math "$monitor_x + $screen_width - $win_width")
    set -l max_y (math "$monitor_y + $screen_height - $win_height")

    if test $pos_x -lt $monitor_x
        set pos_x $monitor_x
    else if test $pos_x -gt $max_x
        set pos_x $max_x
    end

    if test $pos_y -lt $monitor_y
        set pos_y $monitor_y
    else if test $pos_y -gt $max_y
        set pos_y $max_y
    end

    echo "$pos_x $pos_y"
end

function handle
    set -l line $argv[1]
    switch $line
        case "windowtitlev2*"
            # Expected format: windowtitlev2>><id>,<title>
            set -l payload (string replace -r '^windowtitlev2>>' "" $line)
            set -l parts (string split "," $payload)
            set -l window_id (string trim $parts[1])
            set -l title (string join "," $parts[2..-1])

            # Loop over the extensions defined in the JSON file.
            for ext in (jq -r 'keys[]' $zen_json)
                # Get regex, x and y for the current extension.
                set -l reg (jq -r --arg k $ext '.[$k].regex' $zen_json)
                set -l ext_x (jq -r --arg k $ext '.[$k].x' $zen_json)
                set -l ext_y (jq -r --arg k $ext '.[$k].y' $zen_json)

                # Remove any extra surrounding single quotes.
                set -l reg (string trim -c "'" $reg)

                # If the title matches the regex, dispatch floating commands.
                if string match -q -- "$reg" "$title"
                    # Calculate centered position
                    set -l pos (center_window $ext_x $ext_y)
                    set -l pos_x (string split " " $pos)[1]
                    set -l pos_y (string split " " $pos)[2]

                    hyprctl --batch "dispatch togglefloating address:0x$window_id; dispatch resizewindowpixel exact $ext_x $ext_y,address:0x$window_id; dispatch movewindowpixel exact $pos_x $pos_y,address:0x$window_id"
                    return
                end
            end
        ;;
        case "*"
            # Do nothing for other events.
        ;;
    end
end

socat -U - UNIX-CONNECT:/run/user/1000/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock | while read -l line
    handle "$line"
end
