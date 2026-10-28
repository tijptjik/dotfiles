#!/usr/bin/env fish
# The native tool checks freshness; compare the cache to report its real result.
if test -f "$HOME/.local/share/icons/hicolor/256x256/apps/tjikup-notification.png"; and type -q gtk-update-icon-cache
    set -l cache "$HOME/.local/share/icons/hicolor/icon-theme.cache"
    set -l before (stat -c '%y:%s' "$cache" 2>/dev/null)
    set -l cache_output (gtk-update-icon-cache --ignore-theme-index "$HOME/.local/share/icons/hicolor" 2>&1)
    or begin
        printf '%s\n' $cache_output >&2
        exit 1
    end
    set -l after (stat -c '%y:%s' "$cache" 2>/dev/null)
    if test "$before" != "$after"
        printf 'UPDATE  ✓ Icon cache    refreshed\n'
    else
        printf 'SKIP    ✓ Icon cache    no changes\n'
    end
else
    printf 'SKIP    - Icon cache    unavailable\n'
end
