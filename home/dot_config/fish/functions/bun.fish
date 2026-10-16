function bun --description 'Run Bun and its children in a memory-limited scope'
    set -l executable (command --search bun)
    if test -z "$executable"
        echo 'bun: executable not found' >&2
        return 127
    end
    # Preserve the terminal, environment, working directory and exit status.
    # Absolute-path Bun invocations and existing services are unaffected.
    command systemd-run --user --scope --quiet --collect \
        --slice=app.slice --expand-environment=no \
        -p MemoryHigh=16G -p MemoryMax=24G -p MemorySwapMax=2G \
        -p OOMPolicy=kill -- "$executable" $argv
end
