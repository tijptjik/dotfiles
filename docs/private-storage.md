# Private files, Google Drive, and si

Documents, media, projects, and resources are ordinary local folders on fi and
li: `~/documents`, `~/media`, `~/projects`, and `~/resources`. Applications edit
local files immediately, including while offline. `~/code` and the separate
uppercase `~/Documents` directory are outside this workflow.

## Drive layout

- `crypt/`: encrypted rclone storage, unlocked explicitly with a local password.
- `GSUITE/`: destination for Google-native documents. Native files remain cloud-native and are
  excluded from bisync; opening them in Google's applications preserves their
  editing and sharing semantics.
- `public/`: existing public/shared files. Mounting it does not change sharing.
- `private/archives/`: retired material, outside hourly synchronization.
- `private/backups/`: legacy backups and short-term bisync recovery copies.
- `private/documents/`, `private/media/`, `private/projects/`,
  `private/resources/`: the four bidirectional sync destinations.

Existing archives and legacy backup collections remain under
`private/archives/` and `private/backups/`. They are outside the four-folder
hourly client sync; backup jobs do not move or delete them.

## Sharing approval

Domain-wide reader access on `private` and `GSUITE` is approved: the domain
has only the owner as a user. Existing sharing permissions are retained.
`sharing_approved: true` enables synchronization; setting it false blocks both
initialization and ordinary sync without stopping local backups to si.
The verified layout marker is also required for initialization.

## Hourly sync

`private-sync.timer` runs at five minutes past each hour on fi and thirty-five
minutes past on li, with up to a minute of jitter. The service skips until all
four initializations finish. It catches up after login if a scheduled run was
missed; it cannot sync while a device is asleep or offline.

Use `private-storage sync --progress` to run an interactive Drive sync with
rclone transfer progress on one updating line, or `private-storage sync` for
the normal quiet run. Interactive status uses Charmbracelet Gum styling when
`gum` is installed; plain text remains available otherwise.
For a reviewed change that exceeds the 5% delete guard, use
`private-storage sync --progress --max-delete-percent 40 resources` for that
single folder. The 1 GiB deletion-size cap and recovery copies still apply.
Use `private-storage backup` to create and verify the Restic backup on si;
Restic shows progress in an interactive terminal. `private-storage status`
shows the last successful sync, backup, and most recent failure. Logs and
per-folder baselines are in `~/.local/state/private-storage`. They are local
device state: do not copy them to another machine, delete them to clear an
error, or synchronize them.

Protections:

- A lock prevents a local sync and backup from overlapping.
- An availability marker on both sides prevents an unavailable endpoint from
  looking like an intentional empty folder. Do not delete `.private-sync-access`.
- Rclone's bisync deletion percentage limit is 5, with an additional 1 GiB
  deletion-size cap. Large intended deletions require deliberate review; the
  scheduled command never uses `--force` or `--resync`.
- Concurrent edits preserve numbered conflict copies. Desktop notifications
  point to the log; failures also appear in systemd and `last-error.json`.
- Overwritten/deleted files are retained under local `state/recovery` and
  `private/backups/sync-recovery/<host>/<folder>/<timestamp>` for 31 days.
  Cleanup uses the timestamp directory, not the original file's modification
  date, and requires a successful si backup receipt.
- `.git`, `node_modules`, `.venv`, Python caches, application caches, trash,
  and incomplete-download files are excluded. Symlinks are not followed.
  Keep live databases and other files requiring atomic multi-file updates
  outside the shared folders; use application-consistent backup exports.

Initialization is explicit: `private-storage init [folder ...]`. It requires a
verified Drive layout, checks disk headroom, previews the merge, and then merges
both sides. On an initial same-name difference fi establishes the cloud version, retaining
the displaced cloud copy in recovery. li then prefers that established cloud
version, retaining its displaced local copy in recovery. Subsequent runs use the established
baseline and preserve both versions of concurrent changes. The initial service
first backs up existing local files to si, then initializes each folder. A
failed initialization is not silently retried with a forced resync.

## Incremental backups

`private-backup.timer` runs `private-storage backup --scheduled` on fi at
00:00 and li at 01:00, independently of R2 success. li is a fallback: it skips
if another client backup is running, or fi has completed a verified backup
since midnight in li's local timezone. A failed or absent fi backup does not
suppress li. This decision uses si's `.coordination/fi.json` receipt, so fi
need not be online for li to check it.

A server-held lock in `/mnt/storage/private/backups/clients/.coordination/`
prevents overlapping client backups. Completion is recorded only after backup,
repository verification, and retention succeed. Losing the lock connection
stops the local Restic process. Local locks also serialize backup with sync
and R2 archiving. Explicit `private-storage backup` bypasses the completed-fi
skip but still respects the shared lock.

Both hourly sync and daily backup timers use `Persistent=true`: after a missed
schedule, they run once when the user's systemd manager is next available, then
resume their normal calendar. Catch-up is not one run per missed interval.
A policy skip counts as that timer activation; it is not retried later that day.
Network failures are reported, not automatically retried as soon as connectivity
returns. Existing `private-storage-initialize.service` is an explicit bootstrap
workflow, not the ordinary daily backup timer. Restic stores encrypted, deduplicated
snapshots in `/mnt/storage/private/backups/clients/<hostname>` on si. Each device
has its own repository. After each successful backup and repository check, the
job keeps one snapshot in each age band: under 1 day, 1–3 days, 3–7 days,
7–14 days, 14–31 days, 31–92 days, and 92–365 days. For snapshots older than
365 days, it keeps the newest snapshot from each calendar year. This gives daily,
every-three-day, weekly, every-two-week, monthly, quarterly, and annual recovery
points. Identical file content is deduplicated even though each scheduled run
creates a snapshot. Repository locks and pruning only after successful backup
and verification protect against overlapping runs and failed uploads. The first
backup must transfer the baseline and can take hours for large media folders.

The password is recoverable from Bitwarden Secrets Manager as
`PRIVATE_RESTIC_PASSWORD`. Losing that secret prevents restoration.

```sh
private-storage backup
private-storage snapshots --from fi
private-storage restore --from fi --snapshot latest --to ~/restore-private
```

Restore requires a new destination and verifies restored content. Either client
can restore from the other's repository using the same recoverable password.

## Drive archive and Google-native backups

Si runs a separate Restic job daily at 02:00 HKT for
`type-drive:private/archives` and `type-drive:GSUITE`. The job exports Google
Docs, Sheets, Slides, and Drawings to
`docx`, `xlsx`, `pptx`, and `svg`, reads through a read-only rclone mount without
keeping a persistent plaintext mirror, and backs them up to
`/mnt/storage/private/backups/google-drive`. Each source is tagged
and retained independently at **1 daily, 1 weekly, and 1 monthly** snapshot.
The repository is encrypted with `PRIVATE_RESTIC_PASSWORD`, checked after
backup, and pruned only after the checks succeed. A failed transfer or empty
Drive source fails closed and records a failure receipt. The transient mount
lives in Si's user runtime directory and
is unmounted after each source backup. The first baseline may take hours for a
large archive; later runs deduplicate unchanged content.

Si's Drive OAuth config is created once from the Bitwarden
`RCLONE_GOOGLE_DRIVE_CONFIG` secret so rclone can persist token refreshes. It is
separate from Si's existing R2 rclone config. The native-file export preserves
document content and folder names; it does not preserve Google sharing ACLs,
comments, revision history, or native editing semantics. Unsupported or
non-exportable Google file types fail the run instead of silently counting as
backed up. A dangling Drive shortcut has no target content to export; rclone
logs it, and the target must be restored or reattached in Drive before it can
be backed up.

Inspect service status with `systemctl --user status drive-restic-backup.timer`
and logs with `journalctl --user -u drive-restic-backup.service`. The last
successful run receipt, including top-level entry counts, is in
`~/.local/state/drive-restic/last-success.json`; failures are in
`~/.local/state/drive-restic/last-error.json`.
Restore snapshots from the repository on Si with Restic, filtering by the
`private-archives` or `gsuite` tag before restoring into a new directory.

```sh
restic -r /mnt/storage/private/backups/google-drive -p ~/.config/drive-restic/restic-password snapshots --tag gsuite
restic -r /mnt/storage/private/backups/google-drive -p ~/.config/drive-restic/restic-password restore latest --tag gsuite --target ~/restore-gsuite
```

## Mount commands

| Command | File-manager label | Local mount | Remote |
|---|---|---|---|
| `mntcrypt` | `crypt` | `~/.mnt/rclone/crypt` | Drive `crypt:` |
| `mntgiprivate` | `gi-private` | `~/.mnt/google/private` | Drive `private/` |
| `mntgipublic` | `gi-public` | `~/.mnt/google/public` | Drive `public/` |
| `mntsiprivate` | `si-private` | `~/.mnt/si/private` | si `/mnt/storage/private` |
| `mntsipublic` | `si-public` | `~/.mnt/si/public` | si `/mnt/storage/public` |

Google Drive and si both contain `public` and `private` mounts. Their Linux
FUSE device labels include the source (`gi` or `si`) so the file manager shows
four distinct names. Restart an existing mount service for its label to update.

These mounts are writable, cache writes locally, and run in supervised transient
user services named `private-mount-<name>`. A fast file-manager copy is not proof
of upload completion. Check `systemctl --user status private-mount-giprivate`
(or the corresponding name) and wait for zero queued/uploading files before
stopping a mount or shutting down. Keep cached writes until they upload.
The synced local folders do not depend on these mounts.

si connections try its LAN address first, then `ssh.type.hk`, validating the
known SSH host key. `mullvad-exclude` allows these connections outside the VPN.

### Crypt password and credentials

Run `mntcrypt --set-password` in a terminal to choose or change the local mount
password. It reads the recovery configuration from Bitwarden and uses age's
interactive passphrase prompt to create `~/.config/private-storage/crypt.conf.age`.
The password is not passed as a command argument, written in Git, or sent to chat.

`mntcrypt` prompts for that password before decrypting configuration into the
private per-user runtime directory and starting the mount. It is not mounted
at login. Password protection controls local unlocking; an account already
permitted to read the Bitwarden recovery secret can also recover the key.

Bitwarden holds `RCLONE_GOOGLE_DRIVE_CONFIG`, `RCLONE_CRYPT_RECOVERY_CONFIG`, and
`PRIVATE_RESTIC_PASSWORD`. Chezmoi creates the normal Drive configuration only
when the local file is absent, and renders the Restic password into an
owner-only managed file; the crypt recovery key is not rendered in plaintext at
rest. This lets rclone persist routine OAuth token refreshes without Chezmoi
trying to overwrite them. Set a mount password separately on each client.
Reconnect Google OAuth with `rclone --config ~/.config/private-storage/drive.conf
config reconnect type-drive:` when necessary and update the stored Drive
configuration secret after an authorization reset. To reseed a client from that
secret, first preserve its current `drive.conf` if needed, then remove the local
file and run `chezmoi apply ~/.config/private-storage/drive.conf`.

## Deployment and verification

After pulling both dotfiles repositories, `tjikup` installs the managed tools
and enables the hourly and daily timers on clients. On a newly provisioned
client, create the four local directories if absent, preserve any existing
contents, set the crypt password, and start:

```sh
systemctl --user start --no-block private-storage-initialize.service
journalctl --user -fu private-storage-initialize.service
```

Check available disk space before downloading the initial cloud dataset.
Initialization checks each dataset against available local space with a 5 GiB
reserve. Do not initialize a second client until fi's initial merge finishes;
then that client merges with the established cloud copy, retaining displaced
versions in its own recovery directories.

The crypt password file is per device; unlocking requires the password chosen
by its user.
