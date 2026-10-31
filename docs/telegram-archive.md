# Telegram Archive on Si

The authoritative Compose template is `native/home/files/dockers/docker-compose.yaml.j2`;
nginx routing is `system/native/si/files/nginx/sites-available/type.hk`.
The viewer listens only on `127.0.0.1:8096`; nginx serves `tga.type.hk` through
the existing type.hk TLS listener. The deployment captures all accessible chats
and media and transcribes downloaded voice notes locally.

| Service | Pinned image | Access and role |
| --- | --- | --- |
| `telegram-backup` | `drumsergio/telegram-archive:9.5.0` | Telegram collector, live listener, scheduler and transcript reconciliation |
| `telegram-viewer` | `drumsergio/telegram-archive-viewer:9.5.0` | Authenticated viewer at `https://tga.type.hk`, via loopback port 8096 |
| `akou` | `drumsergio/akou:0.5.4` | Private transcription API at `http://akou:8476`; no published port |

## Private runtime configuration

On Si, `/mnt/storage/meta/appData/telegram-archive/` contains:

- `backup.env` (0600): `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`,
  a random `INTERNAL_PUSH_SECRET`, and akou’s `TRANSCRIPTION_API_KEY`.
- `viewer.env` (0600): `VIEWER_USERNAME`, `VIEWER_PASSWORD`, and the same
  `INTERNAL_PUSH_SECRET`. Do not put Telegram credentials in this file.
- `data/session/`: Telegram authorization, mounted only into the collector.
- `data/backups/`: SQLite database and media; shared with the viewer.

Create these directories as UID 1000 with mode 0700. Use the credentials of an
existing app at https://my.telegram.org/apps; a second app is unnecessary.
The viewer uses mandatory authentication, secure cookies, and the origin
`https://tga.type.hk`. Its password is generated privately during setup.

## First login and start

From an interactive SSH terminal on Si:

```sh
# Complete the akou model/key bootstrap below before enabling transcription.
cd /home/m/dockers
docker compose run --rm --no-deps telegram-backup python -m telegram_archive auth
# Enter the Telegram login code and two-step password in this terminal.
docker compose up -d akou telegram-backup telegram-viewer
```

The collector's `telegram` profile prevents unauthenticated startup during an
ordinary stack update. Naming the service explicitly enables it. To include it
in subsequent whole-stack updates, use `docker compose --profile telegram up -d`.
Do not run another collector or auth process against a running session.

All chat types (including bots) and media are captured, with no per-file size limit.
The mounted `all_chats.py` adapter includes archived dialogs in every sweep: upstream
9.5.0 otherwise fetches their list but only captures explicitly allowlisted archived
chats. It preserves upstream filtering, flood handling and pagination, and deduplicates
overlapping dialogs. Recheck this adapter against upstream before changing image versions. The listener
captures new messages and observed edits/deletions; deletion mode is soft.
The scheduler also performs its default daily sweep. Each media attempt has a
30-minute timeout, up to three attempts within a run and a persistent retry
budget of five. Exhausted files remain visible as failures; they do not establish
that the archive is complete. Transcription runs locally through akou; see below.

Normal downtime is recovered by the next history sweep fetching messages after
the last stored message ID. `FILL_GAPS` additionally searches for holes *inside*
stored history; it is not required for ordinary catch-up. Missing IDs can also
represent deleted or inaccessible messages, so gap filling cannot guarantee their
recovery. `FILL_GAPS` and `SYNC_DELETIONS_EDITS` are not enabled in this deployment.
Soft deletion preserves messages whose deletions the archive observes; messages
removed before capture cannot be recovered from Telegram by this setup.

## Verification and maintenance

```sh
cd /home/m/dockers
docker compose ps akou telegram-backup telegram-viewer
docker compose logs --tail=100 telegram-backup
docker compose exec -T telegram-backup python -m telegram_archive stats
docker compose exec -T telegram-backup python -m telegram_archive check-media
```

Review failed/pending media, confirm oldest/newest expected messages, and open
representative downloaded photos and videos before considering the first backup
complete. CLI options follow the pinned release's `--help`.

Stop the backup and viewer services before upgrading their images or making a
consistent filesystem copy of SQLite. Preserve the full archive including relative media symlinks,
session files, and private env files with `rsync -a` or equivalent. A live WAL
copy is not proof of a recoverable database. This service captures Telegram;
its own off-host backup must be verified separately.

## Deployment boundary

Si still uses the pre-migration layouts: home Compose under
`/home/m/code/dotjik/home/dockers/` and nginx under
`/home/m/.local/share/systjik/etc/nginx/`. These are the live server checkout
paths, not the native source paths listed at the top of this guide. The scoped
deployment added equivalent service blocks without upgrading the whole checkout.
The 2026-10-29 comparison confirmed that all four archive helper/config/style
files match native policy byte-for-byte. The Compose blocks are equivalent after
resolving `ports.telegramArchive` to 8096, and the nginx archive block is identical.
Recovery copies of pre-deployment Compose/templates/nginx are kept privately in
`/home/m/.local/state/telegram-archive-setup/`. Reconcile those legacy changes when
Si migrates to native policy; the native files in this repository remain authoritative.

Cloudflare DNS must route `tga.type.hk` through the same proxied origin and origin
port rules as the other Si web applications. DNS and end-to-end HTTPS are separate
acceptance gates from a working origin. Never enable anonymous access to work
around an authentication or proxy failure.

## Viewer styling and WebSocket verification

The pinned viewer uses a browser Tailwind compiler whose first render can omit
layout utilities when Vue mounts. `telegram-archive/tailwind-9.5.0.css` is generated
from that image's served HTML and inline theme using Tailwind 3.4.17. It is mounted
as a single static file; nginx replaces the runtime script tag with this stylesheet
and an empty `window.tailwind` config target. Custom inline styles stay intact.
Do not mount a directory over the app's static assets.

To regenerate after reviewing an image upgrade, fetch its root HTML locally and run
`python3 build_css.py viewer.html tailwind-VERSION.css`. Update the mount and nginx
replacement together, then verify computed login layout, an actual login, and
received WebSocket frames through the public Cloudflare hostname. A 403 WebSocket
handshake while signed out is the app enforcing authentication, not evidence of a
broken Upgrade proxy. The viewer password is in Si's private `viewer.env`.

## Local English/Dutch transcription

`akou` is pinned to `drumsergio/akou:0.5.4`, reachable only on the archive Docker
network at `http://akou:8476`. There is no published host port. Its `fast` preset
uses multilingual Parakeet TDT 0.6B v3 (fp32); language is detected automatically,
and the settings declare English and Dutch. Speaker diarization is off for voice notes.
One worker uses two CPU threads, with Compose limits of two CPUs and 6 GB RAM.

The non-secret `akou-config.json` is managed alongside Compose. Persistent models,
settings/keys, and jobs live under `telegram-archive/akou/{models,data}` in appData.
Before first start, create the bind directories as uid 1000 and run:

```sh
cd /home/m/dockers
docker compose run --rm --no-deps akou models pull fast
docker compose up -d akou
docker exec akou akou keys create --name telegram-archive --scope jobs --json
```

Save the returned API key privately as `TRANSCRIPTION_API_KEY` in `backup.env`;
never put it in `viewer.env` or Git. The archive polls job results, so no callback
secret or public transcription endpoint is needed. Model pulls verify checksums.

Automatic transcription covers voice messages only. The timer runs every 15
minutes with a maximum of five files per account per drain; the live listener also
submits new downloaded voices. Existing downloaded voices are eligible for
backfill. Five is a per-drain batch limit, not a daily or lifetime limit. Original
audio remains intact and transcripts are stored in SQLite.
Akou's temporary job retention (seven days) does not remove transcripts already
stored in Telegram Archive. Back up the archive independently as described above.

### Changing or pausing transcription

Non-secret settings live in Compose's `environment` blocks and
`telegram-archive/akou-config.json`. Credentials live in the private env files.
Compose `environment` takes precedence over `env_file`: adding
`TRANSCRIPTION_ENABLED=false` to `backup.env` will not override the current
Compose setting.

The active collector settings are:

```yaml
TRANSCRIPTION_ENABLED: "true"
TRANSCRIPTION_URL: http://akou:8476
TRANSCRIPTION_PROVIDER: akou
TRANSCRIPTION_PRESET: fast
TRANSCRIPTION_LANGUAGE: ""  # automatic language detection
TRANSCRIPTION_DIARIZE: "false"
TRANSCRIPTION_TYPES: voice
TRANSCRIPTION_BACKFILL_PER_RUN: "5"
TRANSCRIPTION_DRAIN_INTERVAL_MINUTES: "15"
```

Akou's config declares `asr.languages: ["en", "nl"]`, automatic language detection,
one concurrent job and two ASR threads. Keep automatic language detection for a
mixed English/Dutch archive. Audio/video attachments other than voice notes are
not included by the current `TRANSCRIPTION_TYPES` setting.

For a durable pause, set `TRANSCRIPTION_ENABLED: "false"` in both backup and
viewer Compose blocks. Update the authoritative template and Si's corresponding
legacy template/live Compose file together (see Deployment boundary), then run:

```sh
cd /home/m/dockers
docker compose up -d --force-recreate telegram-backup telegram-viewer
```

Restore both values to `"true"` and repeat that command to resume. This preserves
original audio and stored transcripts. Stopping akou alone leaves the collector
submitting to an unavailable API. A simple container restart does not apply
changed Compose environment settings; recreate the affected services. After
changing akou's config, recreate akou too and check all three services' health.

### Five-message pilot — 2026-10-29

Automatic collection was disabled during the pilot. Exactly five distinct,
already-downloaded voice files were submitted through the archive's own
`transcribe_media` client and `reconcile_events` result handling.

| Sample | Audio duration (seconds) | Result |
| --- | ---: | --- |
| 1 | 6.454 | Non-empty transcript stored and retrieved |
| 2 | 10.642 | Non-empty transcript stored and retrieved |
| 3 | 10.974 | Non-empty transcript stored and retrieved |
| 4 | 11.934 | Non-empty transcript stored and retrieved |
| 5 | 29.934 | Non-empty transcript stored and retrieved |

The 69.938 seconds of audio completed in 36.9 seconds, excluding model download
and setup. All five original audio hashes were unchanged. Each transcript was
retrieved through the authenticated public viewer's
`/api/media/{media_id}/transcripts` endpoint and matched its stored text. Private
transcript text and message identifiers are deliberately excluded from this guide.

All output text was English; language metadata was null. Dutch audio and
listening-based word accuracy remain untested. Successful processing is not a
measured word-error rate: review transcripts against audio before treating them
as exact quotations. Automatic voice-only transcription was enabled after the
pilot, and akou, backup and viewer health checks passed.

Separately, public viewer login, styling, authenticated chat API responses and a
WebSocket 101 handshake were verified. Receipt of live WebSocket frames was not
observed during the short check. Full archive completeness and off-host restore
remain separate, unverified acceptance checks.

### References

- [Telegram Archive transcription configuration](https://geiserx.github.io/Telegram-Archive/configuration/transcription/)
- [Telegram Archive listener configuration](https://geiserx.github.io/Telegram-Archive/configuration/listener/)
- [Akou 0.5.4 configuration](https://github.com/GeiserX/akou/blob/v0.5.4/docs/configuration.md)
