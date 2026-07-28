#!/usr/bin/env fish

if command -q fc-cache
    fc-cache -f "$HOME/.local/share/fonts" >/dev/null 2>&1
end
