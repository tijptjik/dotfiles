function zed --description 'Launch Zed in its own memory-limited scope'
    set -l executable (command --search zed)
    if test -z "$executable"
        echo 'zed: executable not found' >&2
        return 127
    end
    "$HOME/.local/bin/zed-isolated" "$executable" $argv
end
