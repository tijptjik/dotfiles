# Cloudflare backups on Fi

## Activation status — verified 25 October 2026, 14:05 HKT

**Implemented, restore-verified and scheduled.** The complete backup finished
at 14:04 HKT; the isolated restore passed at 14:05 HKT, and the weekly timer was
then enabled. Its next run is **1 November 2026 at 03:00 HKT**.

| Evidence | Result |
| --- | --- |
| Snapshot | `ec990711a569ed504570165c2d409c8a70fe32845c4a64cbc4fb2c38d2ead908` |
| DNS | 11 zones, 187 records; restored account and record counts checked |
| KV | 2 namespaces, 1 value; restored value SHA-256 checked |
| R2 | 18 buckets, 39,089 objects, 20,218,714,649 bytes; restored counts and bytes match inventory |
| Repository integrity | `restic check`: no errors found |
| Full isolated restore | All 39,128 restored files verified by Restic |
| Source comparisons | SHA-256 comparisons passed for 14 representative R2 objects, selected from eligible nonempty buckets |
| Completion receipts | `last-success.json`, `restore-verified.json` and `setup-completed.json` agree on the snapshot ID |
| Destination | Exact UUID `E84A8D8F4A8D5B68` mounted read/write; isolated restore directory removed |
| Timer | Enabled and active; Sunday 03:00 HKT, persistent |

Receipts are under `~/.local/state/cloudflare-restic/`. The previous failure
records are retained in `incident-20261025T043915Z`; superseded top-level failure
markers have been cleared. This is verified file recovery. Importing the data
into replacement Cloudflare services remains a separate recovery operation.

The one-time first-restore service has completed. Its private helpers under
`/tmp/cloudflare-token-entry` are no longer needed for normal scheduled backups.
The managed backup service, timer, credentials and verified-restore marker persist
across sessions. A future isolated rehearsal can follow the instructions below.

## Outstanding work

- Push the thread's commits and synchronize the relevant repositories on Li and
  Si. Earlier push approval was rejected; this thread has not pushed these
  changes. Cloudflare backup execution remains Fi-only.
- Check the UUID mount after Fi's next planned reboot. The live writable mount
  and fstab entry are verified; actual boot-time mounting has not been exercised.
- Repeat isolated restore rehearsals periodically; the first full rehearsal
  passed on 25 October 2026.

## Setup and read-failure recovery

The approved disk was mounted writable and the persistent mount installed through
Chezetc. A separate DNS Read token was saved to Bitwarden as
`CLOUDFLARE_BACKUP_API_TOKEN`; the existing token supplies zone settings and KV.
The original preflight found 38,464 R2 objects. Source contents changed during
setup; the verified snapshot's inventory above is authoritative for that snapshot.

Two early runs were interrupted for traversal/concurrency tuning. The 11:24 run
saved partial snapshot `a17562f0` at 12:35 after an R2 index object repeatedly
returned `unexpected EOF`. A subsequent direct read succeeded, and its server
modification time was during the backup, consistent with stale mount metadata.
The destination remained writable with ample free space.

The patched service restarted at 12:39 HKT. Its first pass encountered 42 read
errors in the device-archive bucket and retained partial snapshot `6ba488ef` at
14:00. The bounded retry refreshed exports and the R2 mount, reused 38,924
unchanged files, and completed in approximately 76 seconds. The following
repository check and full restore passed, allowing automatic timer activation.

The job retries Restic's incomplete-source exit code 3 once. It discards only
temporary exports, refreshes DNS/KV/R2 inventory and creates a new read-only
mount. Partial snapshots and the staging path are retained within that invocation.
`--ignore-inode` allows unchanged parent files to be reused despite new synthetic
FUSE inode/ctime values; size and modification time still matter. Other errors
fail immediately. Incomplete attempts never reach success receipts or pruning.
Failure receipts include the program, operation and exit code without command
arguments or object paths.

## Scope

The approved account is `a6eeace4b6d9f8e07ab307964e74d801` (`tijptjik`).

| Content | Export | Current evidence |
| --- | --- | --- |
| Zones, DNS records, zone settings | Cloudflare API JSON, filtered to this account | Export passed: 11 zones and 187 DNS records |
| Workers KV | Namespace/key manifests, metadata, expiry, raw values named by SHA-256 | Independent export passed: 2 namespaces, 1 key |
| R2 | Inventory plus object bodies/names/server modification timestamps through a read-only rclone mount | 39,089 objects, 20,218,714,649 bytes in the verified snapshot inventory |

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
