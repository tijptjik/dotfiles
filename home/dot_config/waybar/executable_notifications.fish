#!/usr/bin/env fish

if test "$argv[1]" = toggle
    dunstctl set-paused toggle
    exit
end

set -l icon ''
set -l state enabled
set -l tooltip 'Notifications enabled'

if dunstctl is-paused 2>/dev/null | string match -q true
    set icon ''
    set state paused
    set tooltip 'Notifications paused'
end

printf '{"text":"%s","class":"%s","tooltip":"%s"}\n' "$icon" "$state" "$tooltip"
