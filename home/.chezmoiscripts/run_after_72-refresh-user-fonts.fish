#!/usr/bin/env fish
if test "$FLEET_DEFER_HOOKS" = 1
    exit 0
end

if command -q fc-cache
    fc-cache "$HOME/.local/share/fonts" >/dev/null 2>&1
end
