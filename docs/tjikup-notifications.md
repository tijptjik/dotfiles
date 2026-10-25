# Tjikup completion notifications

Local desktop runs send one notification with a branded white “up” icon, elapsed
time, completed-stage count and up to three warning/failure subjects. Warning
reports remain visible even when the workflow returns zero (for example, an apply
was skipped). Failures and Ctrl-C use critical urgency. Dry runs are labelled
as previews. Detailed output stays in the terminal; the temporary TSV report is
removed when the process exits.

Fish's `done` plugin excludes direct `tjikup` and fleet shortcut invocations,
including `command tjikup` and absolute paths. Other commands retain their completion notices.
New Fish shells load this automatically. In an existing shell, run:

```fish
source ~/.config/fish/conf.d/tjikup-notifications.fish
```

Local notifications require `notify-send` and a desktop session.

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
are preserved. No reverse SSH connection or remote desktop bus is needed.

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
