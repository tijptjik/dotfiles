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
| All | `.ssh`, `.gnupg`, `.local/share/icons`, `.local/share/backgrounds`, `.local/share/fonts` | Reviewed sync |
| Clients | `.config/Bazecor`, `.var/app/rocks.koreader.KOReader/config/koreader` | Reviewed sync |
| Clients | `.config/sublime-text`, `.config/waybar/crypto` | Exact mirror from `fi` |
| Clients | `.duckdb` | Independent device backups |
| Desktop | `.config/unity3d`, `.var/app/org.yuzu_emu.yuzu/config`, Yuzu data folders listed in the policy | Desktop backups |
| Desktop | `.local/share/device-archives-policy` | Encrypted recovery copy of the archive policy; daily/weekly/monthly retention |
| Desktop | `.codex-lb` | Master backup of `store.db` and its matching `encryption.key` |
| Per client | `.electrum`, `.local/share/keyrings`, `.config/gh`, `.config/gcloud` | Encrypted device-specific recovery snapshots; daily/weekly/monthly retention |
| Desktop | `.keys` | Encrypted independent recovery snapshots; daily/weekly/monthly retention |

SSH and GnuPG conflicts support text diffs. Asset and application conflicts are
reviewed through file lists, sizes, and hashes. `.obsidian` is a chezmoi Git
external. Beekeeper Studio and QGIS are outside this backup policy.

User fonts live in `~/.local/share/fonts`. `~/.fonts` is a compatibility symlink
and is not archived separately. Chezmoi consolidates both locations before
applying files, refuses differing files at the same relative path, and preserves
the original directory under `~/.local/state/font-migration/` for rollback.
Font caches are rebuilt locally; they are not synchronized.

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
| Latest only | Fonts, icons, backgrounds, `.duckdb`, Yuzu user saves, load, screenshots |

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

For guided synchronization, run this on the receiving device:

```sh
device-archives setup --from fi
# Or limit the guided session to selected folders:
device-archives setup .ssh .gnupg --from fi
```

The reviewer has a file list on the left and a scrollable diff/metadata preview
on the right. Every differing file stays in the list, with a visible **pending**,
**accepted**, **rejected**, or **skipped** decision. Revisit any file to change or
undo its decision. The layout adapts to terminal width (minimum 60×10).

| Key | Action |
| --- | --- |
| ↑/↓ or j/k | Select a file; scroll when preview has focus |
| Tab | Switch file-list/preview focus |
| PgUp/PgDn or K/J | Scroll preview |
| a | Accept the source version (including a source deletion) |
| r | Reject the source version; keep local |
| s | Mark this file skipped for now |
| u | Undo its decision |
| A | Accept all pending files; existing decisions stay intact |
| Enter | Continue to final folder confirmation |
| S | Skip the entire folder without applying it |
| q / Esc | Quit without applying this folder |
| ? | Toggle shortcut help |

Pending/skipped files block applying the folder. Decide them or skip the entire
folder: partial review never records a completed synchronization baseline.
Exact mirrors accept source versions only; skip the folder to preserve local
contents. Decisions remain editable after declining the final confirmation.
Decisions are held for the current review session; quitting discards decisions
for the unapplied folder.

The two-pane editor uses Python's terminal support; final confirmation and
error prompts use Gum, with tjikup's status rows around operations. No JSON
editing is required. Final confirmation defaults to No. Verified snapshot,
stale-plan, active-writer, and rollback safeguards remain in effect.

Plans and baselines are maintained automatically. A changed local file, expired
snapshot or active writer still blocks apply; the wizard offers retry with a new
plan or skip. Completed folders stay applied if you cancel later. Once all
selected folders succeed and readiness passes, it offers to back up this device.
Skipped folders suppress that offer; the laptop's initial-sync gate still requires
all nine assigned sync/master folders. Missing Gum or a noninteractive terminal
fails without applying changes. Diffs can contain credentials and are displayed
only in the local terminal, not written into status reports.

The lower-level commands remain available for automation and advanced review:

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
backend stopped. The archive contains a compact recovery database: accounts,
credentials, configuration and schema are retained, while the policy's explicit
`sqlite_recovery.store.db.omit_tables` list removes request/usage history,
historical rollups, audit/automation runs and transient bridge/session records.
Configuration tables for automation jobs, API keys, proxies and limits remain.
Live history is never deleted; cleanup and compaction run only on a consistent
temporary SQLite copy. The copy must pass integrity/foreign-key checks and stay
under 16 MiB or the backup fails before upload, preserving the previous recovery
point. New or changed deletion triggers and missing configured tables also fail
closed. Runtime code and debug logs remain excluded.

This is a configuration/credential recovery backup, not operational history.
Following a restore, history starts afresh and in-progress sessions/operations
are lost. No live account credentials are synchronized between devices.
Restored OAuth tokens may require reauthentication after provider-side rotation.
The 2026-10-25 trial reduced a 975 MiB database to 2.45 MiB, preserved all rows
in 28 retained tables, and verified credential decryption using the matching key.

Sockets, ephemeral locks, SQLite sidecars, and policy exclusions are omitted.
SQLite is copied consistently, but the full directory is not an atomic snapshot
of a running application. Close apps if a backup reports changing files.

## Client and server rollout

Install the current changes in **both** the chezmoi and Chezetc source repositories
before applying. `tjikup` runs the home and system configuration workflows; it
does not complete archive synchronization. A failure during Chezetc apply does
not undo earlier successful stages. Re-running after fixing the failed stage is
safe; review unrelated local changes before allowing tjikup to commit them.

### Laptop (`li`)

1. If tjikup already completed its home stages and stopped during system apply,
   run `chezetc apply` after installing the client installer fixes to complete
   that part; a full tjikup run is not required just for archive sync. The hooks
   build Waybar and install Strata as the invoking desktop user, while package
   dependencies use sudo. Material Symbols can use the Fedora 43 COPR chroot
   when the current Fedora release is unavailable; an already-installed fallback
   needs no repair. Check `~/.local/state/chezetc/waybar-build-failure.log` if the
   custom Waybar build fails. The working system binary remains the fallback.
2. Close Bazecor, KOReader and Sublime Text before applying their sync plans.
   Confirm fi has current successful backups; fi need not remain online while
   li downloads its snapshots from R2.
3. Run `device-archives setup --from fi`. Follow the folder previews, inspect
   diffs, choose local/source for conflicts, and confirm each apply. Do not
   blanket-select fi for SSH/GnuPG differences. The wizard handles plans and
   resolutions internally.
4. Accept the final backup prompt after all nine folders are synchronized.
   If you skip or cancel, run the same command again to continue reviewing;
   completed folder baselines are retained.
5. Confirm `systemctl --user list-timers backup-packages.timer`: daily at 00:15.
   Until initial sync is complete, the enabled timer intentionally skips backups.

ZapZap is managed separately by chezmoi, not these archives. Its template uses
`zapzapConfigs.fi` or `zapzapConfigs.li` from `.chezmoidata/zapzap.json`; tjikup
captures only the current client's configuration, preserving Qt serialization,
window geometry, window state, and recent-download paths on the other client.
Close ZapZap before applying deliberately edited settings; its running process
can otherwise write its old settings back at exit.

### Server (`si`)

1. Install the current repository changes and run `tjikup` after reviewing local
   server edits. Client-only Waybar, Strata and ZapZap configuration is excluded.
2. Run `device-archives ready` and inspect
   `systemctl --user list-timers backup-packages.timer`. Si has no mandatory
   initial-sync gate and backs up its own assigned folders daily at 00:30.
3. Run `device-archives setup --from fi` to review the five shared folders:
   `.ssh`, `.gnupg`, `.local/share/icons`, `.local/share/backgrounds`, and `.local/share/fonts`.
   Preserve server-specific keys and authorization files when resolving
   conflicts. Keep the current SSH session open until access has been checked
   from a second session after applying SSH changes.
4. Accept the final backup prompt after the reviewed sync. Si's snapshots remain
   separate from fi/li, subject to each folder's retention policy.

Neither device receives codex-lb accounts through this workflow. The `.codex-lb`
archive is fi-only recovery data; independent laptop authentication remains a
separate setup task.

## LAN access while using Mullvad

Every chezmoi apply sets Mullvad's persistent LAN-sharing policy to `allow`
when the CLI is installed, including on clients and servers. Hosts without
Mullvad skip this step. This permits local-network SSH while the VPN is on;
it does not disconnect the VPN or change its relay settings.

Recovery credentials in `.keys` are backed up encrypted, but the age identity must also remain recoverable independently (for example in Bitwarden). The encrypted archive cannot recover its own lost decryption identity. These credential folders are recovery backups, not cross-device synchronization.

Zen is delegated to its own sync by user preference. `.zen` is no longer in the
archive policy deployed on Fi and Li. Existing remote Zen and Firefox snapshots
are retained. `.mozilla` also remains unscheduled. Removing the policy
entry means the ordinary restore CLI cannot select `.zen` without temporarily
reintroducing a compatible policy entry. Sync coverage was not audited here.

## Telegram Desktop settings

The separate, unapplied [Telegram policy proposal](telegram-settings-policy.json)
selects these root-level files from
`~/.local/share/TelegramDesktop/tdata`:

```text
settingss
settings0
settings1
shortcuts-custom.json
*.tdesktop-palette
*.tdesktop-theme
```

`settingss` holds global application settings. `settings0`/`settings1` are the
legacy alternate storage slots. Settings carry their own salt and do not need
the account's `key_datas`; see Telegram 7.3.3's
[settings loader](https://github.com/telegramdesktop/tdesktop/blob/v7.3.3/Telegram/SourceFiles/storage/localstorage.cpp).
This internal encryption does not provide backup secrecy: the archive and
manifest still use age encryption because settings can contain private paths
and proxy configuration. Retention is independent per client.

Account keys, account subdirectories, hashed theme/background blobs, messages,
media, caches, logs, dumps, downloaded fonts/emoji/dictionaries, and generated
default shortcuts are excluded. Custom theme exports are retained, but the
active theme may require reimporting because its cached blob is omitted.
Account-specific preferences are not promised by this global-settings backup.

Once the proposal has been activated and a first Telegram backup exists,
restore into a review directory first:

```sh
device-archives restore .local/share/TelegramDesktop/tdata --from fi --to ~/restore-review/telegram-settings
```

For an actual restore, quit Telegram, preserve any existing target settings,
and copy only the reviewed files into the destination `tdata` directory with
private permissions. Replace conflicting `settingss`/`settings0`/`settings1`
slots as one reviewed set so a stale target slot cannot win. Do not replace
the whole `tdata` directory or copy account keys from another installation.
Launch Telegram, sign in afresh if needed, reimport the saved theme, and check
shortcuts, display/notification settings and destination-specific paths.

On 2026-10-25, Telegram 7.3.3 accepted and decrypted Fi's copied global settings
in an isolated working directory without account login keys. The selected
three files totalled 43,399 bytes (42.4 KiB). This startup check is narrower
than verifying every setting after login; those checks remain manual.

Activation status (2026-10-25): local restore tests are complete. This entry is
kept outside the active policy pending approval of the first Telegram upload;
the cache-cleanup rollout does not activate Telegram backups on either client.

## Cache exclusions

The policy excludes Bazecor's Chromium caches, logs, crash files and downloaded
dictionaries; KOReader's render cache; DuckDB's downloaded `extensions/`;
Electrum's `blockchain_headers` and `daemon`; Unity player logs/analytics; and
generated `icon-theme.cache` files. It preserves app settings, wallet files,
reading state, custom assets and game saves. DuckDB currently has no selected
files after excluding extensions, but the folder rule remains to capture any
future user data outside that directory. Current extension metadata identified
all 12 Fi extensions as downloads from the official repository.

These exclusions affect future backup and sync selections. They do not delete
local caches. Existing snapshots are pruned only after replacement readback and
verification succeeds, according to the configured retention policy. See the
[dated content audit](device-archives-content-audit.md) for the measured baseline.

## Personal files on si

Documents, media, projects, and resources use the incremental Restic workflow in
[private-storage.md](private-storage.md). Dedicated client midnight timers run it independently of R2 success,
sharing the backup lock to avoid simultaneous backup processes. Its repositories are under
`/mnt/storage/private/backups/clients/<hostname>`.

Existing age-encrypted documents snapshots remain under
`/mnt/storage/private/backups/device-archives`. Use `document-archives` for
inspection or restoration of those snapshots. They are not part of the daily
Restic job. Both formats retain their own recoverable encryption credentials.
