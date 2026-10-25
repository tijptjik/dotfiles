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
set -l idle_state OFF
if not command pgrep -x hypridle >/dev/null
    set idle_icon ''
    set idle_class caffeine
    set idle_state ON
end

set -l filter_icon '󰖙'
set -l filter_class day
set -l filter_state OFF
if command pgrep -x hyprsunset >/dev/null
    set filter_icon '󰖔'
    set filter_class night
    set filter_state ON
end

switch "$argv[1]"
    case caffeine
        printf '{"text":"%s","class":"%s","tooltip":"Idle Inhibit : %s"}\n' \
            "$idle_icon" "$idle_class" "$idle_state"
    case nightlight
        printf '{"text":"%s","class":"%s","tooltip":"Nightshift : %s"}\n' \
            "$filter_icon" "$filter_class" "$filter_state"
end
