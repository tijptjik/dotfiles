# Tjikup completion notifications

Local desktop runs prefer a native Notjik status card with a branded white “up”
icon. A compact status row shows `ALL SYSTEMS GO`, issue counts such as
`2 failed · 1 warning`, or `INTERRUPTED`, alongside elapsed time and completed-stage
count. The body lists up to three issues, with failures first and a count of any
remaining issues. Entries identify the stage and tool, for example
`Failed · UPDATE: Bun` or `Warning · CHECK: Bitwarden`. Dirty repositories use
friendly names and file counts: `Dirty Chezmoi — 48 files`. This includes staged,
unstaged, and untracked files, so a dirty warning does not mean a tool failed.
A single dirty repository shows its name at the left of the status row and its
file count at the right; elapsed time and stage count appear below the title.
The generic runner failure summary is omitted when specific failures are
available. Other report notes and raw command output stay in the terminal.

On Hyprland, **Show window** returns to the window and workspace that launched the
command. The runner captures the window from its process ancestry at startup;
switching workspaces while it runs does not change the target. It detects Lua
dispatch support and retains the legacy command for older Hyprland versions.
It activates the application window; it does not select an editor's terminal
panel or scroll to the command output. The button is
omitted when no unambiguous originating window is available. Clean cards expire
after ten seconds; warnings and failures remain until dismissed. Failures and
Ctrl-C use critical urgency. Dry runs are labelled as previews. The temporary
TSV report is removed when the process exits.

Fish's `done` plugin excludes direct `tjikup` and fleet shortcut invocations,
including `command tjikup` and absolute paths. Other commands retain their completion notices.
New Fish shells load this automatically. In an existing shell, run:

```fish
source ~/.config/fish/conf.d/tjikup-notifications.fish
```

Local notifications require a desktop session. If `notjikctl` is unavailable or
delivery fails, the runner falls back to `notify-send` with the same result text.

## SSH results on the originating desktop

Use these Fish shortcuts from the machine where you want the completion report:

```fish
sitjikup            # Si: m@ssh.type.hk (Mullvad exclusion when available)
litjikup            # Li: io@li.local
fitjikup            # Fi: io@fi.local
litjikup --dry-run  # Extra arguments are forwarded safely
```

On the named host, the shortcut runs `tjikup` locally. Otherwise it uses SSH with
a terminal allocated for prompts and notifications. The functions autoload in
existing Fish shells after installation. Remote access requires a reachable SSH
server and your existing SSH authentication; the shortcuts do not configure these.
Li uses the managed laptop host-key file when present. Fi and Li's `.local`
addresses require local-network name resolution. From Fi, `fitjikup` needs no SSH.

In a direct Kitty SSH terminal, completion reports travel back through the SSH
PTY using Kitty's OSC 99 protocol. A run on Si or Li therefore notifies Fi when
Fi hosts that terminal. The title includes the remote hostname, for example
`Tjikup · si complete`. Success, warnings, failure urgency and the branded icon
are preserved. The **Focus** button asks Kitty to activate the originating
terminal. No reverse SSH connection or remote desktop bus is needed.

The managed `~/.config/kitty/notifications.py` hook reads structured status
metadata from the remote runner and delivers a native Notjik status card on the
desktop. Only display fields cross SSH; focus actions are generated locally.
If Notjik is unavailable or delivery fails, Kitty keeps its standard text card.
Kitty loads this hook at startup: restart the Kitty application after first
installing it (a new tab or configuration reload is not sufficient).

Interactive SSH sessions work automatically. For a one-line remote invocation,
allocate a terminal:

```sh
ssh -t io@li.local tjikup
ssh -t m@ssh.type.hk tjikup
```

Keep the connection open until completion. Redirected output, unsupported
terminals, and detached/headless jobs do not send desktop notifications. A
multiplexer such as tmux requires terminal-protocol passthrough and is not
automatically configured. The receiving desktop resolves the named
`tjikup-notification` icon from its local installation.

Set `TJIKUP_NOTIFY=0` to disable either notification route. Delivery failure does
not change the workflow exit status. No Kitty configuration change is needed.
