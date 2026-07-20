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

printf '{"text":"%s %s","class":["%s","%s"],"tooltip":"L : hypridle | M : shutdown | R : hyprsunset"}\n' \
    "$idle_icon" "$filter_icon" "$idle_class" "$filter_class"
