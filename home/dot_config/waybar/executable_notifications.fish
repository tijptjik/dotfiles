#!/usr/bin/env fish

if test "$argv[1]" = toggle
    notjikctl toggle >/dev/null
    exit
end

set -l icon ''
set -l state enabled
set -l tooltip 'Notifications : ON'

set -l paused (notjikctl status 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["paused"])' 2>/dev/null)
if test "$paused" = True
    set icon ''
    set state paused
    set tooltip 'Notifications : OFF'
else if test -z "$paused"
    set state unavailable
    set tooltip 'Notification service unavailable'
end

printf '{"text":"%s","class":"%s","tooltip":"%s"}\n' "$icon" "$state" "$tooltip"
