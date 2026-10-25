# Device archive content audit — 2026-10-25

This records the read-only audit baseline of the active policy and selected
files on Fi. The user subsequently authorized the cache exclusions, compact
codex-lb recovery and R2 pruning; see the implementation record below. Audit
figures and reachability limits in the baseline sections are dated observations,
not the post-rollout state.

## Result

The active Fi archives contain **711.98 MiB of clear cache, downloadable runtime
data and logs** that can be excluded from future backups. This is **28.82%** of
the **2.412 GiB** uncompressed payload in the latest locally recorded manifests
for the 26 currently configured folders. These manifests date from 2026-10-23;
the same unnecessary paths were confirmed in the live selections on 2026-10-25.

This is a per-snapshot payload estimate, not measured compressed cloud storage
savings. Historical snapshots retain their old content until an appropriate
retention or separately reviewed cleanup operation removes them.

| Folder | Recorded payload | Clear exclusion candidates | Payload excluded | Remaining payload |
| --- | ---: | --- | ---: | ---: |
| `.duckdb` | 584.18 MiB | Downloaded `extensions/` binaries and metadata for multiple versions | 584.18 MiB | None in the current directory |
| `.electrum` | 72.78 MiB | `blockchain_headers` | 72.77 MiB | 15.76 KiB |
| KOReader config | 41.28 MiB | `cache/` | 40.81 MiB | 481.96 KiB |
| `.config/Bazecor` | 14.00 MiB | Chromium caches, crash data, logs, downloaded dictionaries | 13.78 MiB | 227.12 KiB |
| `.config/unity3d` | 0.46 MiB | Player logs and Unity analytics | 0.44 MiB | 22.72 KiB |

The aggregate above deliberately excludes the less certain candidates below.

## Recommended first changes

### DuckDB

The inspected `.duckdb` contains 12 extension binaries and 12 `.info` files,
all under `extensions/`; it contains no user database or configuration files.
Installed versions include multiple 1.4.x, 1.5.x and 2.0.0 trees, with `spatial`
and `httpfs` dominating size.

Stop archiving `extensions/`, or remove the `.duckdb` folder assignment if this
remains its only content. Record extension names, versions and sources where
needed for reproducibility, then reinstall using DuckDB's extension mechanism.
Check for locally built or unavailable third-party extensions before removing
their only recovery copy. Keep any such exceptional artifacts separately.

### Electrum

Exclude `blockchain_headers`, a rebuildable chain-header store. Also omit the
68-byte `daemon` runtime file; that tiny saving is not in the headline total.
If populated later, inspect `forks/` for equivalent chain data rather than
including it by default.

Keep wallet files, configuration and relevant certificate/trust data. Empty
directories or filenames are not evidence that wallet/seed recovery is covered;
this audit did not inspect credential contents or verify wallet recovery.

### KOReader

Root: `.var/app/rocks.koreader.KOReader/config/koreader`.

Exclude `cache/`, including render caches and `cache/cr3cache/`. This accounts
for 98.9% of the recorded folder payload. Preserve `settings.reader.lua`,
custom defaults, plugins, scripts, style tweaks, and user reading state.

`settings/bookinfo_cache.sqlite3` is another 328 KiB candidate, but confirm it
is entirely regenerable before excluding it. Do not blanket-exclude databases,
`settings/`, reading history, annotations, or book sidecar metadata. Those may
contain persistent user state rather than cached render data.

### Bazecor

Exclude these root-relative directories:

```text
Cache
Code Cache
GPUCache
DawnGraphiteCache
DawnWebGPUCache
Crashpad
logs
Dictionaries
VideoDecodeStats
```

The measured sum is 14,449,163 bytes. `Shared Dictionary/` is a further small
Chromium cache candidate, not counted in that sum.

Preserve `config.json`, `window-state.json`, `Preferences` and application
storage until a keyboard/layout restore verifies where Bazecor keeps macros,
layers and backups. In particular, do not assume `Local Storage`, `WebStorage`
or databases are disposable just because this is an Electron application.

Bazecor and KOReader both use **sync** policies. Their caches therefore enter
the cross-device comparison/merge scope as well as the backup scope. Excluding
them reduces irrelevant changes and potential conflicts, even when compression
makes their remote storage cost smaller.

### Unity games

The inspected folder contains Mini Metro settings/profile data alongside
`Player.log`, `Player-prev.log` and `Unity/<id>/Analytics/`.

Exclude those specific log/analytics paths. Preserve `prefs`, `profile.json`
and any game saves. Do not exclude entire game folders or all JSON files.

## Larger opportunity requiring a separate recovery design

`.codex-lb` already selects only `store.db` and its matching `encryption.key`.
Its runtime, debug logs and other directories are correctly omitted. The
remaining bulk is **inside the database**, so another path exclusion cannot
solve it.

The live database base file measured approximately **974.90 MiB**. Read-only
SQLite page accounting, including each table's indexes, found:

| Table group | Allocated size |
| --- | ---: |
| `request_logs` and indexes | 510.86 MiB |
| `usage_history` and indexes | 317.60 MiB |
| `additional_usage_history` and indexes | 93.17 MiB |
| These three groups combined | **921.64 MiB / 94.54% of the database** |

Other sizable groups include HTTP bridge event history, quota-planner decisions
and historical rollups. There were no free pages in the inspected base file:
this is stored data and indexes, not simply empty space awaiting `VACUUM`.

This inspection used `mode=ro&immutable=1`, so it describes the base database
and does not incorporate concurrent WAL changes. The actual backup engine
uses SQLite's online backup API and includes committed WAL data. No credential,
request-content or database-row values were read into the audit report.

Do not remove `store.db` from backups or blindly omit tables. It also holds
accounts, API keys, proxy settings, automation configuration, quotas and other
state needed for recovery. Usage history can also affect operational behavior.

Recommended follow-up: establish whether codex-lb supports a configuration and
credential export. If not, design a version-aware recovery snapshot using a
consistent temporary database copy, retaining all required tables and relations,
and rehearse restoration with the corresponding encryption key. Only remove
history from that copy after testing its effect. Do not truncate or vacuum the
live service database as part of a backup-size change. No saving from this
proposal is included in the 711.98 MiB estimate.

## Smaller or conditional candidates

- **Sublime Text:** `Local/Session.sublime_session` is 2.14 MiB; nested plugin
  `.git/` directories add about 210 KiB. A session may contain unsaved buffers,
  so treat dropping it as a recovery-scope decision. Git directories may contain
  local commits. Preserve user preferences, keymaps, snippets, custom plugins
  and changes before substituting reinstallable packages. The current rule only
  excludes `Local/Auto Save Session.sublime_session`.
- **Fonts:** 653.67 MiB is actual font/asset payload, not a cache. Hash comparison
  found 66 duplicate-content groups with 70 extra copies totalling **7.64 MiB**.
  Deduplication is optional and separate from cache exclusion; confirm referenced
  paths and provenance first. Do not assume commercial/custom fonts are freely
  reinstallable.
- **Icons:** the 31.71 MiB selection includes an `icon-theme.cache` of 5,060
  bytes that can be rebuilt. Most remaining content is theme/app artwork.
- **gcloud:** `access_tokens.db` is 32 KiB and the update-check file is 135 bytes.
  These are candidates for token regeneration/runtime exclusion, while
  `credentials.db`, ADC credentials and named configurations must remain
  recoverable. The storage benefit is negligible compared with larger items.

## Selections that should remain

- SSH, GnuPG, keyrings, GitHub credentials and `.keys` are small, meaningful
  recovery material. Existing GnuPG socket/lock/random-seed exclusions are
  appropriate. Do not introduce a global rule that discards credential files.
- Wallpapers are 87.74 MiB of user assets. Size alone does not make them caches.
- Yuzu archives already target configuration, keys, saves, modifications,
  play time and screenshots. The selected data is not its broad shader/game
  cache. Preserve those narrow rules; `load/` contains modifications, not a
  generic download cache.
- Waybar crypto already omits `.git`, `__pycache__` and `.pyc` data; the selected
  payload is only about 316 KiB.
- The policy recovery copy is already narrowly selected.
- The live Zen rule selects about 294 KiB from a multi-GiB profile and already
  excludes the large browser storage. The previously prepared removal of Zen
  remains unapplied; it is not a large current payload saving.
- Telegram is not yet in the live policy. Its previously prepared 42.4 KiB
  settings selection remains pending activation.

## Historical archives and coverage limits

Local receipts also exist for retired `.fonts`, `.mozilla`, document archives
and legacy recovery material. They are not part of the current 26-folder
baseline. For example, the historical `.fonts` manifest contains 534.42 MiB,
alongside the newer canonical `.local/share/fonts` archive. This is a candidate
for a separate historical-coverage comparison, not permission to delete it.
Removing a folder from the policy does not prune its old remote snapshots.

The R2 root listing confirmed `fi/`, `li/` and `si/` namespaces. Both recursive
size inventories timed out, including a bulk-list retry; no compressed remote
size or reclaimed-storage claim is made. This audit relied on local saved
manifests and live selections, without downloading encrypted archive contents.

SSH reads of Li and Si failed because their short names did not resolve. The
local Tailscale backend was stopped and had no Li/Si peers available. No network
or service settings were changed to work around that. Fleet-wide live content
and backup freshness therefore remain unverified.

## Implementation and verification order

1. Add the narrow cache/log exclusions above, preserving recovery state and any
   exceptional locally built DuckDB extensions. Do not use a global `*.db`,
   `*.json`, `*cache*`, `*.old`, or temporary-file wildcard across all folders.
2. Test selected archive contents with representative fixtures, including
   persistent files whose names resemble caches. For sync/master folders,
   verify that applying an updated plan preserves excluded local files.
3. Re-measure selected payloads on Fi and reachable clients. Create new verified
   encrypted snapshots and perform focused application restore checks before
   considering old archive cleanup.
4. Investigate codex-lb's recoverable minimum separately; test against the
   installed schema and maintain its database/encryption-key pairing.
5. Only then review retired snapshots and font duplicates as distinct cleanup
   tasks. Historical data may be unique even when its folder is no longer active.

The report itself required metadata/size checks, saved-manifest inspection and
read-only database page accounting. No implementation or tests were changed in
this audit; earlier uncommitted Telegram tests and policy edits were preserved.


## Authorized implementation follow-up

The first exclusions are now implemented in the managed policy: DuckDB
extensions, Electrum chain headers/daemon, KOReader cache, Bazecor caches/logs
(including Shared Dictionary), Unity player logs/analytics and generated icon
caches. Optional Sublime session/Git removal, font deduplication and credential
cache changes were not included. Official download metadata was verified for
all 12 Fi and both Li DuckDB extensions.

The `sqlite_recovery` policy constructs a consistent temporary database, clears
29 explicitly listed history/transient tables, checks foreign keys and database
integrity, and compacts only that copy. All schema objects remain; missing
configured tables, deletion triggers, broken retained references or output over
16 MiB fail before upload. The trial preserved every row in 28 retained tables
and verified 12 encrypted account fields with the original encryption key.
The source database was 1,022,525,440 bytes and its recovery copy 2,568,192 bytes.
Live service history was not modified. Focused tests verify that log-only changes
do not trigger another upload, while credential/configuration changes do.

A bounded per-folder R2 inventory succeeded after the earlier recursive listing
timeouts. It found 48 archive folders, each with one snapshot, containing
1,686,209,856 bytes of snapshot objects (excluding root latest pointers). There
were no older generations to prune before creating smaller replacements.
Retired Firefox/Zen folders retain their sole recovery snapshot.

Li is reachable at its pinned `li.local` SSH name; the earlier short-name lookup
failure did not imply the laptop itself was offline. Its source files matched
the known baseline and its archive service was inactive before rollout.
Telegram remains a separate unapplied proposal, outside the active policy.


### Completed rollout and remote verification

On 2026-10-25 the source changes and live archive policies/code were applied on
**Fi and Li**, with private before-images retained under each host's
`~/.local/state/device-archives/policy-rollout-20261025T*/`. No full Chezmoi hooks
or application restarts were run. Si's live configuration was not changed; its
five existing R2 snapshot folders were retained and checked in the inventory.

Fi created eight verified replacement snapshots and Li created five. Each upload
was downloaded again, hash/decryption/extraction checked, and published before
its old snapshot was removed by retention. The final remote listing confirmed
all 13 old snapshot directories were absent and the replacement IDs matched
both hosts' success receipts. All **48 archive folders still have one snapshot**;
the other 35 snapshot IDs were unchanged, including retired Firefox and Zen.

| R2 snapshot-object storage | Bytes | Approximate size |
| --- | ---: | ---: |
| Before | 1,686,209,856 | 1.57 GiB |
| After | 1,225,031,745 | 1.14 GiB |
| Reclaimed | **461,178,111** | **439.8 MiB** |

These are actual remote sizes of snapshot data, manifests and completion
records, excluding root `latest.json` pointers. They are not the earlier
uncompressed payload estimate. Fonts, wallpapers, unique historical recovery
points, wallets, configuration and game saves were preserved.

The new Fi codex-lb archive body is **89.5 KiB encrypted/compressed**; its whole
R2 snapshot, including manifest and completion record, is 93,805 bytes. An
independent download of snapshot `20261025T050933.856044Z-047b4d4b2944` restored
the 2,568,192-byte database and matching key, passed integrity/foreign-key checks,
confirmed all 29 history tables were empty, and successfully decrypted all 12
populated encrypted account fields. The live service stayed active and its
request/usage history remained populated.

`bash scripts/validate.sh` passed: **157 tests**, including encrypted compact
round-trip, WAL/config preservation, history-only change detection, size limits,
missing tables, trigger/dependency rejection and cache-exclusion fixtures.
Fi's active code and both policy copies were compared with the managed source;
Li performed the same comparison during installation. Repository changes remain
uncommitted. Telegram's proposed entry remains separate and was not activated.
