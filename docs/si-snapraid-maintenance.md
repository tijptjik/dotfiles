# si SnapRAID maintenance

Installed October 21, 2026; times are Asia/Hong_Kong.

- Daily sync at 05:00, with up to ten minutes jitter.
- Sunday scrub at 08:00, with up to ten minutes jitter: 25% of blocks, choosing blocks not scrubbed in at least seven days. This targets a roughly monthly rolling pass, not a guaranteed calendar-month full scrub.
- Persistent systemd timers catch up after shutdown.
- Application backups remain separate: daily 04:00 on si; Sunday 06:00 outbound pull from fi; daily 10:00 fi check/catch-up.

Every maintenance run verifies all seven filesystem UUIDs, writable mounts and the configured data/parity/content layout. It refuses to overlap another SnapRAID process. Sync and scrub serialize with one another and with application backups. No force flags are used.

Sync checks the diff and stops if over 200 files are removed, or if the diff fails or has no complete summary. Built-in SnapRAID protection against empty disks and zero-sized files remains enabled. A stopped job requires review, not automatically raising limits.

Running, unpaused media-writing containers are paused during diff/sync and resumed afterward. Containers already stopped or paused are left alone. Pause ownership is recorded persistently; ExecStopPost and a boot recovery service restore only containers paused by this workflow if a run is interrupted. Read-only media serving stays available. The external VIDEO transfer into meta/downloads is excluded from parity and is not paused. Direct writes to protected media paths should be avoided during a sync; detected file changes can make the run fail.

Scrub does not pause applications. This is periodic integrity sampling, not backup or automatic repair. A recorded scrub failure blocks subsequent automatic sync until investigation and a successful scrub clear it.

## Check status (Fish-compatible)

```fish
sudo systemctl list-timers 'si-snapraid-*'
sudo systemctl status si-snapraid-sync.service si-snapraid-scrub.service --no-pager
sudo journalctl -u si-snapraid-sync.service -u si-snapraid-scrub.service -n 60 --no-pager
sudo cat /var/lib/si-snapraid-maintenance/last-sync-success.json
sudo cat /var/lib/si-snapraid-maintenance/last-scrub-success.json
```

Success receipts are created only after successful scheduled/manual runs; they do not yet exist immediately after initial installation. Failures appear in systemd/journal and, once command execution starts, mode-specific failure JSON. Logs are in `/var/log/si-snapraid-maintenance/`.

For manual maintenance, use the managed units to retain all guards:

```fish
sudo systemctl start --no-block si-snapraid-sync.service
sudo systemctl start --no-block si-snapraid-scrub.service
```

Do not launch these together intentionally; a second job waits for the first.

Managed sources: sibling chezetc `etc/si-snapraid-maintenance/` and `etc/systemd/system/si-snapraid-*`. Update the expected identities deliberately after any future disk replacement.

Initial installation verified systemd units and all disk identities. A read-only current diff returned 110 removed files (mostly sidecars and the prior Black Sun recording path), passing the 200-removal guard. No new sync or scrub was launched during the user's VIDEO transfer. The prior recovery full scrub passed October 20.

## Approved library cleanup sync, October 22

The user-approved removal of `public/library.bak` removed 2,896 tracked files.
A one-time wrapper checked the exact escaped diff paths against the saved old
library inventory before permitting those removals; there were zero unrelated
removals. All normal disk checks, backup serialization and writer pause/resume
remained in place. The guarded sync passed at 00:15:42 HKT. Post-sync status
reported no errors, and all owned container pauses were released.

The temporary unit override was removed and systemd reloaded. The unit again
runs the normal maintenance script with the unchanged 200-file removal limit.
Receipts and the read-only status are preserved under
`/mnt/data/disk42/.recovery-preservation/approved-library-bak-sync-20261022/`.

## Telegram alerts

Installed October 22, using the existing `@starprowlarr_bot` and its existing
private chat. Sync, scrub and writer-resume failures trigger separate systemd
notification jobs, including deletion-gate refusals and failures before the
maintenance script can save a receipt. Alert delivery does not block parity jobs
or bypass their safeguards. A successful run after an incident sends one recovery
notice; ordinary successful runs stay quiet.

An hourly watchdog, `si-snapraid-health.timer`, also checks for missing successes:
36 hours for daily sync and nine days for weekly scrub. It allows currently
running jobs within those limits and alerts on jobs running beyond them.
Unchanged problems are reminded at most once per 24 hours; changed problems
alert immediately. Failed Telegram deliveries retry every five minutes.

The bot configuration is root-only at `/etc/si-notifications/telegram.json` on
the system filesystem, independent of Prowlarr and the array. It is excluded
from Git and included in encrypted `/etc` backups. Its recovery copy is verified
in Bitwarden Secrets Manager, project `dotfiles`, secret `si-snapraid-telegram`.
The managed notifier, units, client-host exclusions and server-only enable hook
are in chezetc. After fresh provisioning, restore the credentials before enabling
the watchdog; normal apply reports a skip if credentials have not been restored.

```fish
sudo systemctl status si-snapraid-health.timer --no-pager
sudo systemctl start si-snapraid-health.service
sudo journalctl -u 'si-snapraid-alert@*' -u 'si-snapraid-recovered@*' -u si-snapraid-health.service -n 40 --no-pager
```

The initial health check passed without alerting. A temporary, clearly labelled
test unit exercised real failure and recovery hooks; Telegram accepted messages
4581 and 4582. The test unit was removed, and neither a real sync nor scrub ran.
Test and incident receipts are under `/var/lib/si-snapraid-notifications/`.
