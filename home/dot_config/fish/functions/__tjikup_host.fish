function __tjikup_host --description 'Run Tjikup on a fleet host with its terminal attached'
    set -l target $argv[1]
    set -e argv[1]
    if test (command hostname -s) = "$target"
        command tjikup $argv
        return $status
    end

    if not contains -- "$target" fi li si
        echo "Unknown Tjikup host: $target" >&2
        return 2
    end

    # Keep the report on the calling machine, so its link survives SSH exiting
    # and works through Herdr's ordinary desktop file opener as well as Kitty.
    set -l state "$HOME/.local/state"
    if test -n "$XDG_STATE_HOME"
        set state "$XDG_STATE_HOME"
    end
    set -l directory
    if not contains -- --dry-run $argv
        command mkdir -p -m 700 "$state/tjikup/logs"
        and set directory (command mktemp -d "$state/tjikup/logs/$target-XXXXXXXXXXXX")
    end
    set -l remote_command (string join ' ' -- tjikup (string escape -- $argv))
    set -l export_path
    if test -n "$directory"
        set export_path /tmp/tjikup-(command basename "$directory").json
        set remote_command (string join ' ' -- env (string escape -- "TJIKUP_TIMING_EXPORT=$export_path") "$remote_command")
    end
    __tjikup_connect "$target" -t "$remote_command"
    set -l update_status $status

    if test -n "$directory"
        # Use the same routing and pinned host identity as the update. Never
        # replay the update command when collecting a report, even on failure.
        set -l collector 'from pathlib import Path; import sys; p=Path(sys.argv[1]); p.exists() or sys.exit(44); sys.stdout.buffer.write(p.read_bytes()); sys.stdout.buffer.flush(); p.unlink()'
        set -l fetch (string join ' ' -- python3 -c (string escape -- "$collector") (string escape -- "$export_path"))
        if __tjikup_connect "$target" -T "$fetch" >"$directory/timings.json.part" 2>"$directory/transfer.log"
            command python3 -c '
import json, os, sys
from pathlib import Path
p = Path(sys.argv[1]) / "timings.json"
part = p.with_suffix(".json.part")
json.loads(part.read_text())
part.replace(p)
p.chmod(0o600)
if sys.stdout.isatty() and os.environ.get("TERM") != "dumb":
    columns = int(os.environ.get("TJIKUP_COLUMNS") or os.get_terminal_size().columns)
    color = os.environ.get("TJIKUP_COLOR") != "0" and "NO_COLOR" not in os.environ
    title = "\033[36mTask timings\033[0m" if color else "Task timings"
    st = chr(27) + chr(92)
    row = "REPORT  ↗ \033]8;;" + p.as_uri() + st + title + "\033]8;;" + st
    if columns >= 40:
        note = p.parent.name[:columns - 24]
        row += " " * (columns - 23 - len(note))
        row += "\033[2m" + note + "\033[0m" if color else note
    print(row)
else:
    print("Task timings: " + str(p))
' "$directory"
            or echo "Could not read task timings: $directory" >&2
        else
            set -l transfer_status $status
            # No report is expected if the update stopped before applying.
            # Keep diagnostics in the private directory for transfer failures.
            if test "$transfer_status" -ne 44
                echo "Could not collect task timings: $directory/transfer.log" >&2
            end
        end
    end
    return $update_status
end

function __tjikup_connect --argument-names target tty_mode remote_command
    if contains -- "$target" fi li
        command fleet-ssh "$target" "$tty_mode" "$remote_command"
    else
        set -l ssh_options "$tty_mode" -x -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3
        if type -q mullvad-exclude
            command mullvad-exclude ssh $ssh_options m@ssh.type.hk "$remote_command"
        else
            command ssh $ssh_options m@ssh.type.hk "$remote_command"
        end
    end
end
