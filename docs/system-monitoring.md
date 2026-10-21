# System hang recordings

Atop records system and per-process CPU, RAM, swap, disk I/O, and kernel pressure
statistics every 10 seconds. The system service starts at boot, independently of
the desktop session. Daily recordings live in `/var/log/atop/atop_YYYYMMDD` and
are pruned after seven days by atop's daily rotation (age-based, not a size cap).
Files are readable only by root. Sampling can miss very short-lived processes.

## Install or update

Apply the managed files, then install their system configuration:

```sh
chezmoi apply ~/.config/system-monitoring/atop ~/.config/system-monitoring/atop-service.conf ~/.local/bin/setup-system-monitoring
~/.local/bin/setup-system-monitoring
```

The setup command installs Fedora's `atop` package if needed, copies the managed
configuration into `/etc`, enables the recorder and daily rotation, and restarts
the recorder when its configuration changes. It requires sudo.

## Investigate a hang

After a restart, choose the date and time of the hang (local time):

```sh
sudo atop -r /var/log/atop/atop_20261018 -b 22:15 -e 22:26
```

Use `t` / `T` to move forward / backward between samples. Use `C` to sort by CPU,
`M` by memory, `D` by disk activity; `m` shows memory details and `d` disk details.
Compare memory and swap exhaustion, pressure stalls, disk utilization, and the
processes consuming those resources. Do not treat an OOM victim as necessarily
the process that caused exhaustion.

Correlate with the previous boot's kernel and service logs:

```sh
journalctl -b -1 -k
journalctl -b -1 --since '2026-10-18 22:15' --until '2026-10-18 22:26'
sudo systemctl status atop.service atop-rotate.timer
```

The journal is already persistent on this host. Recordings survive a reboot,
but a hard power-off can lose the last buffered samples. A kernel or storage
stall can also stop the recorder itself; the last samples before the gap remain
useful. This setup collects evidence; it does not prevent hangs.
