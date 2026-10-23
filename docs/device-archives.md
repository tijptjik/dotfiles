# Device archives and synchronization

`device-archives` backs up folders to R2 and creates reviewable synchronization
plans. Chezmoi installs the tool, policy, and systemd units. Backups preserve each
machine's state; they do not apply sync plans or resolve conflicts.

## Devices and folder assignments

`~/.config/archive-policy.json` defines device groups matching chezmoi's roles:

| Selector | Hostnames |
| --- | --- |
| `desktop` | `fi` |
| `laptop` | `li` |
| `server` | `si` |
| `clients` | `fi`, `li` |
| `all` | `fi`, `li`, `si` |

Each folder has a `devices` list. It accepts group names, explicit hostnames,
or a mixture; overlapping selections are deduplicated. For example:

```json
".ssh": {
  "devices": ["all"],
  "mode": "sync",
  "review": "content",
  "encrypted": true,
  "retention": "daily-weekly-monthly"
}
```

| Devices | Folders | Policy |
| --- | --- | --- |
| All | `.ssh`, `.gnupg`, `.local/share/icons`, `.local/share/backgrounds`, `.fonts` | Reviewed sync |
| Clients | `.config/Bazecor`, `.var/app/rocks.koreader.KOReader/config/koreader` | Reviewed sync |
| Clients | `.config/sublime-text`, `.config/waybar/crypto` | Exact mirror from `fi` |
| Clients | `.duckdb`, `.mozilla` | Independent device backups |
| Desktop | `.config/unity3d`, `.var/app/org.yuzu_emu.yuzu/config`, Yuzu data folders listed in the policy | Desktop backups |
| Desktop | `.codex-lb` | Master backup of `store.db` and its matching `encryption.key` |

SSH and GnuPG conflicts support text diffs. Asset and application conflicts are
reviewed through file lists, sizes, and hashes. `.obsidian` is a chezmoi Git
external. Beekeeper Studio and QGIS are outside this backup policy.

Inspect assignments:

```sh
device-archives devices all
device-archives devices clients server
device-archives devices fi
device-archives status --devices clients
# --targets is an alias for --devices on status.
```

These selectors inspect assignments; they do not execute commands over SSH.
Backups always run on the current machine and write only its own namespace.
Source arguments also accept single-device aliases, such as `--from desktop`
or `--left desktop --right laptop`. Use a single hostname for restore/diff;
a multi-device group is not a valid source.

## Automatic schedules

Each host runs `backup-packages.timer` using its local timezone:

| Host | Daily start |
| --- | --- |
| `fi` | 00:00 |
| `li` | 00:15 |
| `si` | 00:30 |

The timer has no randomized delay. `Persistent=true` catches up a missed run
when the machine's user manager starts again. User lingering keeps the user
manager available without an interactive login. Sleeping or powered-off
machines run after they resume/start; the timer does not wake them.

The service runs `device-archives ready` as an execution condition, then
`device-archives backup`. The policy's `initial_sync_required` list controls
which devices must complete their first sync before backing up. It contains
`li`: its timer stays enabled, but backups are skipped until every assigned
sync/master folder has a receipt from `fi`. An empty list permits independent
backups immediately, without applying any synchronization.

```sh
systemctl --user list-timers backup-packages.timer
systemctl --user status backup-packages.service
journalctl --user -u backup-packages.service -n 50
device-archives ready
device-archives backup                 # all folders assigned to this host
device-archives backup .ssh .gnupg      # selected assigned folders
device-archives backup .ssh --force    # recreate even if unchanged
```

Before creating a snapshot, the tool compares the folder with its last verified
manifest. Unchanged folders report `SKIP ✓ ... no changes`: no regular-file
staging, compression, encryption, or upload occurs. The summary counts backed-up,
unchanged, and failed folders separately.

The private local `~/.local/state/device-archives/hash-cache/` stores SHA-256
hashes with device/inode, size, nanosecond modification/change times, and mode.
Regular files with unchanged metadata reuse their hashes; other files are hashed
again. Additions, deletions, symlink targets, permissions, root permissions,
and content/encryption policy changes are checked. Excluded files do not trigger
a backup. SQLite databases always use a consistent temporary snapshot, including
committed WAL data, to compare with the archived database.

Skipping requires a matching verified local manifest/receipt, matching remote
latest/completion metadata, and the existing remote archive objects. These small
remote metadata checks do not download the archive. Missing remote objects cause
a new backup. Hash caching alone never marks an upload successful. Unchanged
checks keep the original snapshot date; retention still runs, and identical
contents do not produce duplicate daily/weekly/monthly archives. `--force`
creates and verifies a fresh snapshot when an explicit refresh is needed.

Interactive backups use fixed columns for status, progress, folder, entry
count, compressed size, result, and elapsed time, using the tjikup palette.
Numbers are right-aligned; long folder names are shortened in the middle.
Narrow terminals put the numeric columns on continuation lines. Full folder
names remain available through `device-archives status`. Unknown sizes display
`—`, including unchanged folders whose archives are not downloaded. The active
row becomes a verified result only when the operation completes. Ctrl-C reports
`ABORT` and exits with status 130 without a Python traceback. Terminal progress refreshes every five seconds;
noninteractive logs report phase changes and a heartbeat every 30 seconds.

The tool takes a nonblocking local lock so manual and scheduled jobs cannot
race. A failed folder is reported, other folders are attempted, and the command
exits nonzero if any folder failed. Upload failures never count as successful
backups. Server application/Restic backups are separate from this schedule.

## Storage, encryption, and retention

Snapshots use timestamp-plus-random identifiers:

```text
r2-tijpdata:tijpdata/acrhives/<machine>/<folder>/<snapshot>/
    tree.tar.zst.age
    manifest.json.age
    complete.json
r2-tijpdata:tijpdata/acrhives/<machine>/<folder>/latest.json
```

Backgrounds and Yuzu user saves use plaintext `tree.tar.zst` and
`manifest.json`. All other folders use age encryption with the chezmoi keypair.
Keep `~/.keys/chezmoi.txt` recoverable separately. Each snapshot records its
format; readers support both encrypted and plaintext snapshots.

A backup stages files, detects concurrent changes, and captures SQLite databases
through the online backup API. It uploads the archive and manifest, downloads
them again, checks their hashes, decrypts when necessary, extracts, and verifies
every file before publishing completion and latest pointers. Manifests record
file hashes, permissions, symlinks, empty directories, and changes since the
machine's previous successful snapshot. Plaintext pointer metadata contains
snapshot identity, time, encryption format, and object checksums.

Retention runs after a verified backup, independently per machine and folder:

| Retention | Folders |
| --- | --- |
| Daily / weekly / monthly | `.codex-lb`, KOReader config, Sublime Text, SSH, GnuPG, Bazecor, Waybar crypto, Unity config, Yuzu config, keys, system saves, play time |
| Latest only | Fonts, icons, backgrounds, `.duckdb`, `.mozilla`, Yuzu user saves, load, screenshots |

Daily/weekly/monthly means **at most three snapshots**: the latest successful
snapshot, the newest from the previous ISO calendar week, and the newest from
the previous calendar month. Retention boundaries use UTC. Empty tiers are
omitted; a snapshot qualifying for two tiers occupies one slot. A failed backup
keeps the previous good snapshots and does not trigger pruning.

```sh
device-archives history .mozilla --from desktop
device-archives prune                  # preview local-machine retention
device-archives prune --apply          # validate latest, then remove old snapshots
```

Pruning only removes completed snapshots for folders assigned to the current
machine. Legacy root-level objects and incomplete uploads are outside this
retention operation. A pinned sync plan can expire when its snapshot is pruned;
regenerate that plan before applying it. Local sync baselines survive pruning.

## Reviewed synchronization

Create plans on the receiving device:

```sh
device-archives sync --from desktop
device-archives sync .ssh --from fi
device-archives review /path/to/plan.json
device-archives review /path/to/plan.json --file config
```

Planning does not change application files. Text diffs may contain credentials;
keep them local. Binary and large files are compared through manifest metadata.
For conflicting paths, provide a JSON mapping to `local` or `source`:

```json
{"config": "source", "known_hosts": "local"}
```

```sh
device-archives apply /path/to/plan.json --resolutions /path/to/decisions.json
# Conflict-free plans do not need --resolutions.
```

On first contact, local-only files stay local, source-only files are added, and
different versions at the same path require review. An absent source file alone
is not evidence of deletion. After a successful sync, the saved source manifest,
snapshot ID, and `last_synced_at` establish the baseline:

- Changed only locally: keep the local edit, addition, or deletion.
- Changed only in the source: apply the source change, including a known deletion.
- Changed differently on both sides: require review, including edit/delete conflicts.
- Same resulting state: no conflict.

Master-mirror folders accept only `fi` as their source. Applying a master plan
makes the managed file set match the source exactly. Excluded files are kept.
Reviewed folders can propagate changes back deliberately: back up the laptop,
plan/review/apply from `li` on `fi`, then back up `fi` before another device pulls.

Apply rejects changed local files, changed policies/baselines, and active file
writers. It verifies the pinned snapshot, builds a separate tree, preserves a
sibling `.archive-recovery-*` directory, swaps, verifies, and records success.
Remove recovery directories manually after checking the result. Receipts,
baselines, plans, and transactions live under `~/.local/state/device-archives/`.

## Compare and restore

```sh
device-archives diff .mozilla --left desktop --right laptop
device-archives diff .ssh --left fi --right si --file config
device-archives restore .mozilla --from li --to ~/restore-review/firefox-li
device-archives restore .mozilla --from fi --snapshot SNAPSHOT_ID --to ~/restore-review/firefox-fi
```

Restore requires a new, nonexistent destination. It never merges into a running
application directory. Inspect the restored tree, close the application, and
install the chosen state while retaining the old one.

For codex-lb, restore `store.db` and `encryption.key` together with the desktop
backend stopped. The archive contains neither the runtime nor debug logs and
does not synchronize live account credentials. Restored OAuth tokens may require
reauthentication after provider-side rotation.

Sockets, ephemeral locks, SQLite sidecars, and policy exclusions are omitted.
SQLite is copied consistently, but the full directory is not an atomic snapshot
of a running application. Close apps if a backup reports changing files.
