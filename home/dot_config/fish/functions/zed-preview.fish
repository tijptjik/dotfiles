function zed-preview --description 'Launch Zed Preview in its own memory-limited scope'
    "$HOME/.local/bin/zed-isolated" "$HOME/.local/zed-preview.app/bin/zed" $argv
end
