# si television acquisition and Plex ingestion

Configured October 21, 2026. Scope: Sonarr television downloads in Transmission.

## Flow

1. Existing Sonarr RSS/automatic-search settings select releases for monitored episodes. The title restriction rejects explicit executable-looking releases, but a title cannot reveal hidden torrent contents.
2. Transmission uses a daily 09:00–17:00 Asia/Hong_Kong schedule at 50 KB/s download and upload, with both directions uncapped outside those hours. This replaces the temporary connectivity-testing limits. The server init hook enforces the schedule at startup; its mutable settings remain covered by application backups. Existing paused jobs remain paused; no bulk missing-library search was launched.
3. si-media-guard.timer checks every 15 seconds after each completed run. Once torrent metadata is available, it checks files for Windows executables/scripts/shortcuts. Completed payloads with an MZ header are also rejected even if renamed as video. Only torrents matched to Sonarr's queue are modified.
4. Unsafe torrents are stopped, blocklisted in Sonarr, and removed from Transmission WITHOUT deleting their downloaded bytes. Sonarr is asked for a replacement. At most three immediate replacement requests are allowed per hour globally to contain bad-source loops; later rejections are blocklisted without requesting another immediate replacement. Receipts are in /var/lib/si-media-guard/.
5. Unpackerr 0.16.1, pinned by image digest, polls Sonarr every minute and extracts supported archives after a two-minute completion delay. It has no command hooks, runs as UID 1000/GID 950 with no capabilities, and retains original torrent archives. Its configured Sonarr extraction limits are the application's defaults (20 GB, 1,000 files, 5:1 ratio, eight nested levels). Legitimate releases exceeding these limits need review.
6. Sonarr completed-download handling validates and imports eligible media, renames episodes with the existing naming convention, and uses hardlinks where possible.
7. A tested Plex Server notification triggers library updates on import/download, upgrade and rename. It maps Sonarr /data paths to native Plex /mnt/storage paths and connects through the Docker host gateway, avoiding dependence on the site's LAN address.

The old Transmission completion extraction hook is disabled to avoid competing extractors. Its init script now preserves that setting after container recreation. The old extractor source remains for reference but is no longer mounted by the managed Compose configuration.

## What was found and verified

One 992,648-byte .exe in an old Jujutsu Kaisen cache folder had a Windows PE header. It was not executed. It was copied into the root-only dated media-flow preservation quarantine on disk42, SHA-256 verified, and removed from the import/download folder. This is an unsafe payload, not proof of its exact malware behavior.

No current torrent manifest contained executable extensions at inspection. The guard successfully inspected 26 Sonarr-associated torrents; 65 torrents existed overall. Fixture tests covered deceptive suffixes, rejection ordering, preservation of download data, and containment when Sonarr's API fails.

Unpackerr connected successfully to Sonarr and retrieved 56 queue rows. Plex's notification connection test passed. Sonarr's renaming, completed-download handling and failed-download replacement are enabled. No new completed archived episode was available to prove a real acquisition-to-Plex pass during setup.

This cannot identify every fake release before metadata arrives, guarantee all download sources are safe, or guarantee availability of a valid replacement. Executables are never run. Password-protected archives without known passwords and import/extraction failures remain visible for review; do not run installers or download codec/password tools.

## Status

```fish
sudo systemctl status si-media-guard.timer --no-pager
sudo journalctl -u si-media-guard.service -n 30 --no-pager
sudo docker logs --tail 40 unpackerr
```

Review Sonarr Activity/Queue for import or extraction errors. Guard file checks do not scan unrelated software torrents.

## Managed state

- chezmoi: Compose unpackerr service and Transmission init-hook change.
- chezetc: etc/si-media-guard/guard.py and systemd service/timer, excluded from client hosts.
- Unpackerr secret-bearing config: /mnt/storage/meta/appData/unpackerr/unpackerr.conf; included in application backups, not version control.
- Sonarr integration/settings are in its backed-up application database.
- Pre-change Sonarr DB, config exports, Compose and hook: /mnt/data/disk42/.recovery-preservation/2026-10-21-media-flow/.
- Unpackerr is included among the containers paused during scheduled SnapRAID sync.

## Movie coverage added October 21

The same 15-second guard now routes Sonarr and Radarr queue entries to the correct
application for blocklisting/replacement. One unavailable catalog is reported as a
failed check without preventing the other catalog from being processed. The global
three-replacement-per-hour limit is shared across both apps; payload bytes remain
preserved.

Radarr has a new executable-title custom format scored -10,000 in all seven
quality profiles; existing positive scores cannot override rejection. Other quality
preferences and score thresholds were preserved. Unpackerr now also polls Radarr,
retaining original archives. A separate tested Plex notification updates the movie
library after imports, upgrades and renames. Existing movie renaming and completed
download handling were already enabled.

During initial setup Radarr's Transmission client remained disabled, preserving
the earlier acquisition pause. Recovery acquisition was explicitly resumed later
on October 21 as recorded below. Pre-change Radarr DB,
profiles, notifications and Unpackerr config are preserved under the dated
2026-10-21-radarr-safety recovery directory. Source changes are persisted in chezetc;
secret-bearing integration settings are covered by application backups.

## Completion-hook conflict check

Rechecked live Transmission RPC, on-disk settings, source templates, startup hook,
cron/systemd references and extractor processes. Live completion hooks were off,
but saved JSON and the native settings template still contained old enabled values.
Corrected the saved values and made the template disable them on server hosts.
Aligned the server source checkout too. A disposable-settings rehearsal confirmed
startup keeps extraction disabled and preserves unrelated settings.

Unpackerr was the only running extractor. The existing Transmission container still
has the old script bind mount until its next recreation, but its callback is disabled
and empty; managed Compose removes the mount on recreation. No Transmission restart
or transfer interruption was required.

## Targeted loss recovery resumed October 21, 2026

After relocation, the user authorized reacquisition. Reconciled the historical
exports with live catalogs and physically checked the existing files bracketing
gap seasons. Selected 249 aired missing episodes: 232 with outage-period file
evidence plus additional internal season gaps (121 gaps overlap that evidence).
All selected episodes are monitored and verified in Wanted, including episodes
inside unmonitored seasons. Previously disabled Futurama and MasterClass were
reactivated only for two and six selected gaps respectively; other episodes and
future seasons remain effectively unmonitored.

Verified actual file import/deletion/rename history for 23 fileless movies and
retained their existing quality profiles. The unrelated never-owned Wanted
backlog was not submitted for bulk search. Tested both Transmission connections
and enabled Radarr's client. Added `My Daughter Is a Zombie (2025)`, TMDB 1306816,
Radarr 4674, using the existing 1080p-only profile 4. Its automatic search grabbed
a 1080p WEB-DL and the torrent manifest contains MKV/NFO/TXT files.

Resumed exactly two existing safe paused recovery torrents; other paused jobs
were not resumed. Submitted explicit searches for the other 247 episodes, the
23 historical movies and the new film. Search commands run in the applications'
background queues; submission and grabs are not evidence of completed imports.
The executable-payload guard and Unpackerr remain active, with normal completed
download handling, renaming and Plex notifications. The daily Transmission
bandwidth schedule remains unchanged.

Consistent pre-change SQLite snapshots, private configuration rollback records,
monitoring and command receipts are under
`/mnt/data/disk42/.recovery-preservation/media-reacquisition-20261021T225039/`.
Sanitized target lists and initial progress are under
`/home/m/downloads/media-reacquisition-2026-10-21/` on si. These records contain no
credentials in Git. No existing media files were deleted or overwritten.

## Book, music and indexer integration checks, October 22

Bookshelf now maps Transmission's `/data/meta/downloads/` to
`/mnt/storage/meta/downloads/`. Ephemera's SABnzbd-compatible interface was
disabled; it is enabled again with `/ingest` as the completed directory and
`/downloads` as incomplete, matching its actual container mounts. Bookshelf maps
`/ingest/` from `anna.type.hk` to
`/mnt/storage/meta/downloads/drops/booklore/`. Both download-client connection
tests pass. Ephemera's global downloads pause remains enabled. Its saved
Grimmory/Booklore refresh token expired; an authenticated reconnect through
Ephemera settings is still required for automatic Grimmory uploads. No account
passwords or authorization roles were changed.

EZTV's Cloudflare challenge is handled by the existing ByParr proxy tag. 1337x's
old `.to` endpoint returned Forbidden; its supported `.st` mirror passes through
the same solver. Actual Prowlarr searches returned 147 EZTV and 20 1337x results;
downstream Bookshelf/Lidarr 1337x tests also pass. Prowlarr application sync was
run. LazyLibrarian's API was disabled and had no configured key; a dedicated key
was configured in both applications, and its authenticated API and Prowlarr test
pass. These app settings are in encrypted application backups, not Git.

Lidarr's actual Tidal configuration is `/data/tidal-config`, not the stale
`/config/lastUser.json`. Its token refreshed successfully and a read-only album
search returned 474 Tidal releases. Tidal and Transmission download clients
remain disabled deliberately while music reacquisition is deferred. The
no-client/invalid-assigned-client health warnings reflect that deliberate pause,
not failed Tidal authentication. No music or book acquisition was launched.

Consistent Bookshelf/Ephemera pre-change SQLite copies, private settings rollback
records and test receipts are under
`/mnt/data/disk42/.recovery-preservation/service-repairs-20261022/`.

### Corrected non-video loss inventory

The original 378 missing Navidrome paths were not 378 missing recordings. A
current catalogue/filesystem comparison found counterparts for 366 paths.
Hyperbubble's 27 historical paths map to the 13 retagged album files by unique,
identical durations. Crystal Castles' 2012 album exists as `(III)` in AAC; all
12 files have audio streams and ffprobe durations within 0.1 seconds of the old
MP3 entries. The only remaining music item is the unidentified old Musepack
recording of Vivaldi's *The Four Seasons*, 12 movements. Identify its performer
and edition before seeking an exact replacement. This reconciliation does not
constitute a full audio integrity audit or delete historical catalogue entries.

The two missing audiobook recordings are Isaac Asimov's *Asimov's Mysteries*
(Lazar) and Clive Barker's *Books of Blood: Volumes One to Three* (Jim Zeiger).
The Simon Vance volumes 1–6 recording is present. No owned ebook loss is
confirmed; historical Grimmory record 2101 is unidentified. Individual *Sandman*
#14 and #37 records remain unresolved and may have collected-edition coverage.
The 620 Lidarr and 2,137 Bookshelf Wanted entries are unrelated acquisition
backlogs, not outage loss counts.

Corrected `CURRENT-REVIEW.md`, the 378-row counterpart audit and the 12-row rich
unmatched music export are under
`/home/m/downloads/missing-media-2026-10-21/` on si, with a local copy under
`/home/io/downloads/missing-media-2026-10-21/` on fi. Original exports remain intact.
