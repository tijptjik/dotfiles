# Cloudflare backups on Fi

## Activation status

Setup is authorized. On 25 October 2026 the correct disk was writable, with
495 GiB free. The managed executable, credential file, and user units were
installed, and the persistent mount was added to Chezetc and Fi's `/etc/fstab`.
The initial export rehearsal found that the existing `CLOUDFLARE_API_TOKEN`
lacked DNS Read permission. A separate DNS read token was entered through a
hidden terminal prompt, saved to Bitwarden as `CLOUDFLARE_BACKUP_API_TOKEN`, and
verified by secret readback. The job uses that token for DNS records and the
existing token for zone metadata/settings and KV.

The complete export preflight passed: 11 zones, 187 DNS records, 2 KV namespaces,
1 KV key, and 18 R2 buckets containing 38,464 objects / 20,409,698,437 bytes.
The first backup started on 25 October 2026 at 11:13 HKT. Two early attempts were
interrupted to improve R2 traversal and read concurrency; neither produced a
snapshot. The current attempt started at 11:24:51 HKT. The weekly timer remains
disabled until the first snapshot and an isolated restore have succeeded.

A one-time `cloudflare-backup-first-restore.service` is running independently of
the chat. It waits for this backup invocation to succeed, requires a fresh success
receipt, then restores the entire snapshot with `--verify` into an isolated,
owner-only directory on Fi's internal disk. It validates DNS counts, every KV
value's SHA-256, R2 object/byte counts, and representative R2 source hashes before
removing its temporary restore and enabling the timer. Completion writes
`~/.local/state/cloudflare-restic/setup-completed.json`; failure writes
`setup-failure.json` and sends a desktop notification. No verified snapshot or
restore is claimed until these receipts exist.

This initial completion service is transient and uses private helpers under
`/tmp/cloudflare-token-entry`. It survives the chat ending, but not a reboot.
After an interrupted setup, inspect both journals and complete the isolated
restore below before enabling the timer. Its wait limit is 12 hours.

## Outstanding work — 25 October 2026, 11:51 HKT

The implementation and credentials are committed locally. The live first backup
has read approximately 6.3 GiB of 19 GiB (33% by bytes); no successful snapshot,
restore, or setup-completion receipt exists yet. The old `last-failure.json`
records the deliberately interrupted earlier attempt, not a new transfer failure.

- Finish the running first snapshot and its repository integrity check.
- Let `cloudflare-backup-first-restore.service` perform the full isolated restore,
  content verification, source sample comparisons, and conditional weekly-timer
  activation. These steps are already running/waiting under systemd and need no
  further approval. Inspect `setup-failure.json` and both service journals if the
  completion job fails.
- Confirm `last-success.json`, `restore-verified.json`, and `setup-completed.json`
  agree on the snapshot ID; confirm the timer is enabled with its next run shown.
- The [policy map](fleet-backup-map.md) and [iconographic atlas](fleet-backup-atlas.md)
  now show implementation complete and the first run active, with verification
  and weekly activation pending. Update them to verified/weekly-active only after
  matching receipts and timer evidence exist.
- Push the thread's committed changes and synchronize the relevant repositories
  on Li and Si. Pushing to `main` was blocked by automatic approval review and
  remains pending explicit approval. Cloudflare backup execution stays Fi-only.
- Check the UUID mount after Fi's next planned reboot. The live writable mount
  and fstab entry are verified; actual boot-time mounting has not been exercised.

Unrelated email-archive changes in the shared checkout are outside this thread's
commit scope.

## Diagram status refresh — approximately 12:07 HKT

The running attempt had read about 60% of the expected bytes and reported one
input/output read error; the rclone log also contains unexpected-EOF errors.
No successful-backup, restore, or setup-completion receipt exists at this check.
The run was left in progress. Its final result and any failed object need review;
the initial verification gate remains in force. The diagrams label the route
implemented / first run active, with verified coverage and weekly activation
pending.

## Scope

The approved account is `a6eeace4b6d9f8e07ab307964e74d801` (`tijptjik`).

| Content | Export | Current evidence |
| --- | --- | --- |
| Zones, DNS records, zone settings | Cloudflare API JSON, filtered to this account | Export passed: 11 zones and 187 DNS records |
| Workers KV | Namespace/key manifests, metadata, expiry, raw values named by SHA-256 | Independent export passed: 2 namespaces, 1 key |
| R2 | Inventory plus object bodies/names/server modification timestamps through a read-only rclone mount | 38,464 objects, 20,409,698,437 bytes in the preflight inventory |

This is not a complete Cloudflare account backup. D1 databases, Durable Objects,
Workers deployments and secrets, Access/Tunnel configuration, and other products
are excluded. R2 custom S3 metadata is not guaranteed. Exports are collected over
time, not as a transaction across products; changing or expired objects/keys may
make a run fail. API permissions determine visibility, so scope reductions need
review. The job rejects an empty zone/namespace list and fewer than 18 R2 buckets.

## Destination and schedule

- Device UUID: `E84A8D8F4A8D5B68`, Fi's secondary 1 TB NTFS disk.
- Repository: `/run/media/io/E84A8D8F4A8D5B68/BACKUP/cloudflare-restic`.
- Chezetc manages a UUID-based, writable `nofail` mount at boot. The current
  busy drive was not remounted during setup. Reboot behavior remains untested.
- Every repository operation checks the exact mount point, UUID, writable state,
  and absence of symlink redirection. A missing disk never falls back to root.
- `cloudflare-restic-backup.timer`: Sunday 03:00 Asia/Hong_Kong, persistent
  catch-up when Fi's user manager becomes available.
- Retention: one weekly and one monthly snapshot, grouped by host/tags and
  restricted to the Cloudflare tag/host. These can select the same snapshot.
  The first successful run does not prune; later successful runs do.
- API staging files live in a private temporary directory and are removed after
  each run. R2 is mounted read-only without a VFS file cache. Recursive directory
  prefetch, a 24-hour directory cache, and server modification timestamps avoid
  repeated listings and per-object metadata requests. Every run creates a fresh
  mount/cache. The job uses a process lock and 32 Restic file readers to tolerate
  R2 request latency without staging a second copy of the object bodies.
- Failures are recorded in `~/.local/state/cloudflare-restic/last-failure.json`
  and the systemd journal; a critical desktop notification is attempted.
  Notifications require a working desktop session.

The Chezmoi activation hook enables the timer only when
`~/.local/state/cloudflare-restic/restore-verified.json` and the credential files
exist. Do not create that marker before completing a restore check.

## Credential recovery

No credential values belong in Git, shell arguments, logs, or documentation.

- Restic encryption: Bitwarden Secrets Manager `PRIVATE_RESTIC_PASSWORD`, secret
  ID `90f34958-6254-4b0c-bc65-b4ed0026bee2`; managed owner-only file
  `~/.config/private-storage/restic-password`. Losing it makes the repository
  unrecoverable. Access to Bitwarden must be available independently of Fi.
- DNS records: Bitwarden `CLOUDFLARE_BACKUP_API_TOKEN`, secret ID
  `5608d86b-b32f-4656-88e2-b4ee00347d28`; managed owner-only file
  `~/.config/private-storage/cloudflare-backup-token`. It supplies DNS Read.
- Zone metadata/settings and KV: existing Bitwarden `CLOUDFLARE_API_TOKEN`, secret
  ID `c2cdd91d-02c8-4d31-83ed-b497007da128`; managed owner-only file
  `~/.config/private-storage/cloudflare-config-token`. It supplies Zone Read,
  Zone Settings Read, and Workers KV Storage Read for the approved scope. The
  shared credential is not modified or replaced by this backup setup.
- R2 source reads: existing `r2-tijpdata:` remote in the owner-only
  `~/.config/rclone/rclone.conf`. That credential is needed to fetch new backups,
  not to decrypt an existing Restic repository. Source credentials are not
  included in the Cloudflare snapshot.

After recovering Bitwarden access, apply only the relevant credential files with
Chezmoi; never print their rendered contents. Restore rclone configuration from
the existing device-archive recovery route or provision a replacement R2 read
credential. The R2 remote must expose all expected account buckets.

## Run and inspect

```sh
cloudflare-restic-backup --dry-run
systemctl --user start --no-block cloudflare-restic-backup.service
journalctl --user -u cloudflare-restic-backup.service -f
journalctl --user -u cloudflare-backup-first-restore.service -f
cat ~/.local/state/cloudflare-restic/last-success.json
cat ~/.local/state/cloudflare-restic/setup-completed.json
systemctl --user list-timers cloudflare-restic-backup.timer
```

The dry run performs live API exports and R2 listings but does not initialize,
write, or prune the repository. A real success receipt includes the snapshot ID,
completion time, and DNS/KV/R2 counts. Restic's normal `check` validates structure;
it does not read every stored data blob.

## Isolated restore rehearsal

Before any Restic command, confirm `findmnt --mountpoint` reports the exact UUID
above, the expected path, and `rw`. Stop if anything differs or the path traverses
a symlink. Set these non-secret environment variables:

```sh
export RESTIC_REPOSITORY=/run/media/io/E84A8D8F4A8D5B68/BACKUP/cloudflare-restic
export RESTIC_PASSWORD_FILE="$HOME/.config/private-storage/restic-password"
restic snapshots --host cloudflare --tag cloudflare
```

Restore an explicit snapshot ID into a newly created owner-only directory on a
volume with enough room. Use `restic restore SNAPSHOT --target DIRECTORY --verify`.
The snapshot contains `tmp/cloudflare-restic-*/dns`, `kv`, `r2/inventory.json`, and
`r2-mount/BUCKET/OBJECT`. Never restore over a working tree or live application.

Check the restored DNS JSON counts, each KV manifest's value sizes and SHA-256
hashes, and R2 object/bucket counts. Compare representative restored R2 bodies
with fresh read-only source downloads. Record the snapshot ID, checked scope,
timestamp, and results in the private `restore-verified.json` receipt, then enable
the timer with `systemctl --user enable --now cloudflare-restic-backup.timer`.
Enabling a persistent timer may immediately run a catch-up backup.

This verifies local file recovery. Importing DNS, rehydrating KV with appropriate
expiry semantics, or uploading R2 data into a replacement account is a separate
operation requiring its own target review. Do not replay expired KV values as
permanent keys.
