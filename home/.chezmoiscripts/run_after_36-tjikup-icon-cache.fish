#!/usr/bin/env fish
# Kitty resolves remote notification icons on this desktop by theme name.
if test -f "$HOME/.local/share/icons/hicolor/256x256/apps/tjikup-notification.png"; and type -q gtk-update-icon-cache
    set -l cache_output (gtk-update-icon-cache --force --ignore-theme-index "$HOME/.local/share/icons/hicolor" 2>&1)
    or begin
        printf '%s\n' $cache_output >&2
        exit 1
    end
end
