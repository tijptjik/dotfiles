#!/usr/bin/env fish

function toggle_idle
    if command pgrep -x hypridle >/dev/null
        command pkill -x hypridle
    else
        hypridle >/dev/null 2>&1 &
    end
end

function toggle_filter
    if command pgrep -x hyprsunset >/dev/null
        command pkill -x hyprsunset
    else
        hyprsunset >/dev/null 2>&1 &
    end
end

switch "$argv[1]"
    case toggle-idle
        toggle_idle
        exit
    case toggle-filter
        toggle_filter
        exit
    case shutdown
        systemctl poweroff
        exit
end

set -l idle_icon '󰒲'
set -l idle_class idle
if not command pgrep -x hypridle >/dev/null
    set idle_icon ''
    set idle_class caffeine
end

set -l filter_icon '󰖙'
set -l filter_class day
if command pgrep -x hyprsunset >/dev/null
    set filter_icon '󰖔'
    set filter_class night
end

switch "$argv[1]"
    case caffeine
        printf '{"text":"%s","class":"%s","tooltip":"L: toggle caffeine | M: suspend"}\n' \
            "$idle_icon" "$idle_class"
    case nightlight
        printf '{"text":"%s","class":"%s","tooltip":"L: toggle night light | M: shutdown"}\n' \
            "$filter_icon" "$filter_class"
end
