#!/usr/bin/env fish
if command -q fc-cache
    set -l output (env LC_ALL=C fc-cache --verbose "$HOME/.local/share/fonts" 2>&1)
    or begin
        printf '%s\n' $output >&2
        exit 1
    end
    if string match -q '*: caching, new cache contents:*' -- $output
        printf 'UPDATE  ✓ Fonts    cache refreshed\n'
    else
        printf 'SKIP    ✓ Fonts    no changes\n'
    end
else
    printf 'SKIP    - Fonts    unavailable\n'
end
