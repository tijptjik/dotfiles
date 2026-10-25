function __tjikup_host --description 'Run Tjikup on a fleet host with its terminal attached'
    set -l target $argv[1]
    set -e argv[1]
    if test (command hostname -s) = "$target"
        command tjikup $argv
        return $status
    end

    set -l destination
    set -l ssh_options -t -x -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3
    switch $target
        case si
            set destination m@ssh.type.hk
        case li
            set destination io@li.local
            if test -f "$HOME/.config/codex-lb/laptop-known-hosts"
                set -a ssh_options -o 'UserKnownHostsFile=~/.ssh/known_hosts ~/.config/codex-lb/laptop-known-hosts'
            end
        case fi
            set destination io@fi.local
        case '*'
            echo "Unknown Tjikup host: $target" >&2
            return 2
    end

    # SSH joins its command arguments; escape each value for the remote Fish shell.
    set -l remote_command (string join ' ' -- tjikup (string escape -- $argv))
    if test "$target" = si; and type -q mullvad-exclude
        command mullvad-exclude ssh $ssh_options $destination "$remote_command"
    else
        command ssh $ssh_options $destination "$remote_command"
    end
end
