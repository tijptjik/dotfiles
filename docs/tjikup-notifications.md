# Tjikup completion notifications

Local desktop runs send one notification with a custom house/check icon, elapsed
time, completed-stage count and up to three warning/failure subjects. Warning
reports remain visible even when the workflow returns zero (for example, an apply
was skipped). Failures and Ctrl-C use critical urgency. Dry runs are labelled
as previews. Detailed output stays in the terminal; the temporary TSV report is
removed when the process exits.

Fish's `done` plugin excludes direct `tjikup` invocations, including `command
tjikup` and absolute paths. Other commands retain their completion notices.
New Fish shells load this automatically. In an existing shell, run:

```fish
source ~/.config/fish/conf.d/tjikup-notifications.fish
```

Notifications require `notify-send` and a desktop session. They are skipped over
SSH and on headless hosts. Set `TJIKUP_NOTIFY=0` to disable them. Delivery failure
does not change the workflow exit status. No Kitty configuration change is needed.
