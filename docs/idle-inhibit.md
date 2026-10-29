# Idle inhibition

The Bartjik coffee switch saves its choice in
`~/.local/state/idle-inhibit/state`. `on` means automatic idle actions are
inhibited; `off` enables the normal Hypridle policy, including suspend after
30 minutes. The icon continues to reflect whether Hypridle is actually running.

Tjikup initially adopts the current graphical session's setting. A first
installation without a graphical session retains the automatic-idle default.
Subsequent applies preserve the saved choice and do not start Hypridle.
The service checks the saved choice at login, so inhibition survives session
restarts and reboots. Each machine keeps its own preference outside Git.

Use the bar switch or `idle-inhibit on` / `idle-inhibit off` to change the
setting. Avoid starting or killing Hypridle directly, which does not update the
saved preference. Middle-click on the bar switch still explicitly suspends.

This setting controls Hypridle's dimming, locking, screen blanking, and idle
suspend. Lid handling, critical-battery actions, and explicit suspend commands
are separate. Startup locking remains independent of idle inhibition.

## Other bar modes

Night filter uses the same mechanism through `nightlight on`, `off`, or
`toggle`, storing its choice in `~/.local/state/nightlight/state`. Apply adopts
the current filter state once and never starts the filter. Login starts the
systemd service only when the saved preference allows it. Dimming commands use
the running filter's IPC and cannot accidentally launch a disabled filter.

Notjik saves Do Not Disturb in its own `preferences.json` state file. The bar,
`notjikctl pause/resume/toggle`, and the history drawer's Resume button all
update it. This requires the updated Notjik application alongside these dotfiles.

Desktop/game display mode already persists in `$XDG_STATE_HOME/hypr/display-mode`
(normally `~/.local/state/hypr/display-mode`), which Hyprland reads on startup
and configuration reload. This desktop-only choice remains separate from the
laptop's monitor layout. These preferences are per machine and stay outside Git.
