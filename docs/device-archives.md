# Device archives and synchronization

`device-archives` owns application archives. Chezmoi installs the tool and
`~/.config/archive-policy.json`; it no longer extracts these directories on
`chezmoi apply`. `.obsidian` remains a chezmoi Git external.

## Policies

| Policy | Folders | Behavior |
| --- | --- | --- |
| Reviewed sync | `.ssh`, `.gnupg`, `.local/share/icons`, `.local/share/backgrounds`, `.fonts`, `.config/Bazecor`, `.var/app/rocks.koreader.KOReader/config/koreader` | Three-way comparison; conflicting paths require a per-file decision. |
| Master mirror | `.config/sublime-text`, `.config/waybar/crypto` | Only `fi` can be the source. Applying a plan makes the managed file set exactly match its snapshot. |
| Device backup | `.duckdb`, `.mozilla` | Independent histories; restore from either machine into a new staging directory. |
| Desktop backup | Existing Unity and Yuzu folders | Only `fi` backs these up. |
| Master backup | `.codex-lb` | Only `fi` backs up `store.db` and its matching `encryption.key`. No runtime, debug logs, or obsolete database copies. Never synchronized into the laptop backend. |

Beekeeper Studio and QGIS are no longer backed up or declared for installation.
Existing local app data, installed packages, and old remote archives are not
removed by this migration.

All new archives and manifests use age encryption, including backgrounds and
Yuzu saves that previously had unencrypted archives. The recipient and identity
are the existing chezmoi age keypair. Keep that identity recoverable separately.

## Remote layout and verification

Each snapshot gets a new timestamp plus random ID:

```
r2-tijpdata:tijpdata/archives-v2/<machine>/<folder>/<snapshot>/
    tree.tar.zst.age
    manifest.json.age
    complete.json
r2-tijpdata:tijpdata/archives-v2/<machine>/<folder>/latest.json
```

Snapshots are immutable and retained indefinitely; there is no automatic pruning
in this initial implementation. A machine only writes its own prefix. `latest`
is a pointer for that machine and folder, not a shared archive. Plaintext pointer
metadata contains machine, folder, timestamp, and encrypted-object checksums;
file names, contents, permissions, hashes and change lists are inside the
encrypted manifest.

A backup stages files and checks for concurrent changes. SQLite files use the
online backup API and pass `quick_check`; database WAL/journal sidecars are not
archived. The snapshots contain modes, symlinks, empty directories and SHA-256
hashes, plus additions/modifications/removals since the machine's previous
successful snapshot. It uploads, downloads the encrypted objects again, checks
their hashes, decrypts, extracts and verifies every file before publishing
`complete.json`, `latest.json`, and the local success receipt. Any failure leaves
the previous latest pointer intact until the verified snapshot publication step.

This is not an atomic snapshot of an entire live application. Close apps for
sync/restore and if a backup reports changing files. Sockets are omitted. The
policy explicitly excludes ephemeral locks/caches, GNUPG sockets/random seed,
the fonts UUID, Sublime's autosave session, and the crypto checkout's `.git` and
Python cache. Exact mirroring applies to managed files; excluded files are kept.
An excluded file blocking a directory replacement fails safely.

## First deployment: fi, then li

On `fi`:

```sh
device-archives backup
```

This must finish successfully before the laptop's first sync. Old shared R2
objects are left intact. The legacy `r2upload` and `chezmoi-externals-backup`
entry points now route to the safe per-machine backup command.

On `li`, in the second migration step:

```sh
device-archives sync --from fi
```

This only creates plans, displaying their file paths, changes and conflicts.
It does not alter directories. Inspect each plan:

```sh
device-archives review /path/to/plan.json
# For text files, especially SSH and GNUPG configuration:
device-archives review /path/to/plan.json --file config
```

Text diffs can contain credentials; keep them local. Binary/large files are
reviewed through file metadata rather than decoded text. To resolve conflicts,
create a JSON file with an explicit decision for each conflicting path:

```json
{"config": "source", "known_hosts": "local"}
```

Then apply the pinned plan:

```sh
device-archives apply /path/to/plan.json --resolutions /path/to/decisions.json
# No resolutions argument is needed for a conflict-free plan.
```

The tool rejects stale plans if local files or the sync baseline changed, and
refuses to replace a directory while another user process has files open for
writing inside it. It
verifies the pinned remote snapshot, builds the result separately, retains a
complete sibling recovery directory, swaps in the result and checks it before
recording success. Transaction receipts and sync manifests live in the private
`~/.local/state/device-archives/` directory. The receipt includes the recovery
path; remove old recovery directories manually only after checking the result.

After all nine reviewed/master folders have synced from `fi`:

```sh
device-archives ready
device-archives backup
systemctl --user enable --now backup-packages.timer
```

The first laptop backup is refused until these sync receipts exist. Chezmoi also
leaves the backup timer disabled until this gate passes. Daily backups do not
apply sync plans, overwrite local settings, or resolve conflicts automatically.

## Additions and deletions

On first contact there is no common baseline: a file only present locally stays
local; a file only present in the source is added; different versions at the
same path require review. An absent source file alone is not proof of deletion.

After a successful sync the source manifest, source snapshot ID and
`last_synced_at` become the baseline. With that evidence:

- Changed only locally: keep the local change, including a local deletion.
- Changed only in the source: apply the source addition/edit/deletion.
- Changed differently on both sides: require review, including edit/delete conflicts.
- Same result on both sides: no conflict.

A new local file is preserved even when its parent directory disappeared on the
source. File/directory structural conflicts fail for review. A repeated sync
continues comparing local differences against the last source manifest rather
than silently adopting them as a common baseline.

Reviewed folders can propagate back deliberately: after `li` has synced and
backed up, run `device-archives sync .ssh --from li` on `fi`, review/apply, then
back up `fi` before pulling its new snapshot on `li`. The master-mirror folders
never accept `li` as a source.

## Compare, select, and restore

Compare the two latest backups without applying anything:

```sh
device-archives diff .mozilla --left fi --right li
device-archives diff .ssh --left fi --right li --file config
device-archives history .mozilla --from fi
```

Restore either machine's snapshot into a new directory for inspection:

```sh
device-archives restore .mozilla --from fi --to ~/restore-review/firefox-fi
# Pin an older snapshot returned by history:
device-archives restore .mozilla --from li --snapshot SNAPSHOT_ID --to ~/restore-review/firefox-li
```

The destination must not exist. This avoids replacing a live browser/profile or
silently combining incompatible databases. After inspection, close the affected
app and install the selected recovered tree while retaining the old one.

For codex-lb:

```sh
device-archives restore .codex-lb --from fi --to ~/restore-review/codex-lb
```

Only restore the database and matching encryption key together, with the desktop
backend stopped. Keep the installed runtime separately. Restored tokens may need
reauthentication if they have since rotated; restoring files does not undo token
rotation at the provider. The laptop continues to use the desktop tunnel.

## Operations

```sh
device-archives status
systemctl --user status backup-packages.timer
journalctl --user -u backup-packages.service -n 50
```

The tool takes a nonblocking per-machine lock to prevent manual and timer jobs
from racing. A failed folder is reported and the backup command exits nonzero;
other folders still get an opportunity to back up. R2 upload errors never count
as a successful backup. The existing Si/Restic application backups are separate
and unchanged.

## Migration verification — 2026-10-23

All 20 `fi` folders were uploaded into `archives-v2/fi` and passed encrypted
remote readback, extraction and file-manifest verification. The codex-lb snapshot
was independently restored through the CLI: SQLite `quick_check` passed, four
active accounts were present, and the encryption key matched the desktop.
The safe daily timer is enabled on `fi`.

The tool is installed on `li`, with its backup timer disabled. Read-only plans
for all nine sync/master folders validated access to the encrypted snapshots.
Nineteen conflicting paths require review (SSH, GnuPG, Bazecor and KOReader).
No sync plan was applied and no `li` snapshot was created. The initial plan index
is `~/.local/state/archive-migration/initial-sync-review.json` on `li`; regenerate
plans if local files change before the second step.

Validation included 23 automated tests for three-way merges, first-sync safety,
conflict decisions, active-writer rejection, stale plans, rollback after failed
swaps, cross-device restore/diff, encrypted roundtrips, SQLite WAL consistency,
and failed/corrupt uploads. Final verification receipts are in
`~/.local/state/archive-migration/verification.json` on `fi`.
