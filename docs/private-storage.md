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

`private/media` contains the former archived images plus files merged from
clients. The former Drive media collection is retained in
`private/archives/media`. The old root archives and backups belong under private.
Legacy backups are preserved for content review; they are not automatically
classified as redundant merely because new backups exist. Other unclassified
root files are not moved into synced folders automatically.

## Sharing approval

Google synchronization is blocked while `sharing_approved` is false in
`~/.config/private-storage/config.json`. Both initialization and ordinary sync
check this gate; chezmoi preserves the blocked policy until its source config
is explicitly updated after review. Local backups to si remain independent.

The existing `private` and `GSUITE` folders have domain-wide reader access.
Approval requires deciding whether to retain that access or remove folder-level
domain grants, while preserving individual document shares. The root Google-native
documents remain in their original locations pending this decision.
The layout-ready marker alone does not authorize synchronization.

## Hourly sync

`private-sync.timer` runs at five minutes past each hour on fi and thirty-five
minutes past on li, with up to a minute of jitter. The service skips until all
four initializations finish. It catches up after login if a scheduled run was
missed; it cannot sync while a device is asleep or offline.

Use `private-storage sync` to run now, and `private-storage status` for the last
successful sync, backup, and most recent failure. Logs and per-folder baselines
are in `~/.local/state/private-storage`. They are local device state: do not copy
them to another machine, delete them to clear an error, or synchronize them.

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

`private-backup.timer` runs `private-storage backup` on fi (00:00) and li
(00:15), independently of R2 success. A shared backup lock serializes it with
R2 archiving. Restic stores encrypted, deduplicated
snapshots in `/mnt/storage/private/backups/clients/<hostname>` on si. Each device
has its own repository and retention: **1 daily, 1 weekly, 1 monthly**. Only new
content chunks transfer; unchanged contents skip creating another snapshot.
Repository locks, a check after backup, and retention after successful backup
protect against overlapping runs and failed uploads. The first backup must
transfer the baseline and can take hours for large media folders.

The password is recoverable from Bitwarden Secrets Manager as
`PRIVATE_RESTIC_PASSWORD`. Losing that secret prevents restoration. Original
age-encrypted document snapshots remain recoverable with `document-archives`
under `/mnt/storage/private/backups/device-archives`; daily backups now use Restic.

```sh
private-storage backup
private-storage snapshots --from fi
private-storage restore --from fi --snapshot latest --to ~/restore-private
```

Restore requires a new destination and verifies restored content. Either client
can restore from the other's repository using the same recoverable password.

## Mount commands

| Command | Local mount | Remote |
|---|---|---|
| `mntcrypt` | `~/mnt/rclone/crypt` | Drive `crypt:` |
| `mntgiprivate` | `~/mnt/google/private` | Drive `private/` |
| `mntgipublic` | `~/mnt/google/public` | Drive `public/` |
| `mntsiprivate` | `~/mnt/si/private` | si `/mnt/storage/private` |
| `mntsipublic` | `~/mnt/si/public` | si `/mnt/storage/public` |

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
`PRIVATE_RESTIC_PASSWORD`. Chezmoi renders the normal Drive configuration and
Restic password into owner-only files; the crypt recovery key is not rendered
in plaintext at rest. Set a mount password separately on each client. Reconnect
Google OAuth with `rclone --config ~/.config/private-storage/drive.conf config
reconnect type-drive:` when necessary and update the stored recovery credentials
after an authorization reset. Routine access-token refreshes are written locally.

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

The four public/private mount commands have been exercised on fi. The crypt
password file is per device; unlocking requires the password chosen by its user.

## Legacy Drive backup review

The retained legacy collection is about 104 GB across 203,002 files. Its top-level
categories are Android, DB, credentials, drives, hkghostsigns, images, and system.

| Collection | Coverage decision |
|---|---|
| `system/system.all.20240425`, `system/system.clients.20241203` | Overlap with managed configuration and current R2 archives. Review file coverage before deleting; older app state may be unique. |
| `credentials` | Current secrets use Bitwarden and encrypted R2 recovery. Old credentials still need a content comparison; retained. |
| `DB/breadline`, `hkghostsigns` | Not covered by merely having source code on GitHub. Retained. |
| Android and phone/Telegram images | Historical device data; not assumed identical to the active media collection. Retained. |
| `drives/FoodWorks`, `drives/m@droste.hk` | Historical drive collections, outside active client sync. Retained. |

New client recovery snapshots go to Restic on si. New short-term bisync recovery
copies go to `private/backups/sync-recovery`. Reproducible `/opt` binaries do not
need new Drive backups: their pinned installers are committed in Chezmoi/Chezetc.
The existing external `.tools` safety archive remains independent of this cleanup.
