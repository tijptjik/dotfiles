# Telegram Archive on Si

The authoritative Compose template is `native/home/files/dockers/docker-compose.yaml.j2`;
nginx routing is `system/native/si/files/nginx/sites-available/type.hk`.
The viewer listens only on `127.0.0.1:8096`; nginx serves `tga.type.hk` through
the existing type.hk TLS listener. Both images are pinned to 9.5.0.

## Private runtime configuration

On Si, `/mnt/storage/meta/appData/telegram-archive/` contains:

- `backup.env` (0600): `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`,
  and a random `INTERNAL_PUSH_SECRET`.
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
cd /home/m/dockers
docker compose run --rm --no-deps telegram-backup python -m telegram_archive auth
# Enter the Telegram login code and two-step password in this terminal.
docker compose up -d telegram-backup telegram-viewer
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

## Verification and maintenance

```sh
cd /home/m/dockers
docker compose ps telegram-backup telegram-viewer
docker compose logs --tail=100 telegram-backup
docker compose exec -T telegram-backup python -m telegram_archive stats
docker compose exec -T telegram-backup python -m telegram_archive check-media
```

Review failed/pending media, confirm oldest/newest expected messages, and open
representative downloaded photos and videos before considering the first backup
complete. CLI options follow the pinned release's `--help`.

Stop both services before upgrading images or making a consistent filesystem
copy of SQLite. Preserve the full archive including relative media symlinks,
session files, and private env files with `rsync -a` or equivalent. A live WAL
copy is not proof of a recoverable database. This service captures Telegram;
its own off-host backup must be verified separately.

## Deployment boundary

Si still uses the legacy source layouts as of this setup: home Compose under
`/home/m/.local/share/chezmoi/home/dockers/` and nginx under
`/home/m/.local/share/chezetc/etc/nginx/`. The scoped deployment adds equivalent
service blocks there without upgrading the server's entire policy checkout.
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
uses multilingual Parakeet TDT v3; language is detected automatically, and the
settings declare English and Dutch. Speaker diarization is off for voice notes.
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
backfill. Original audio remains intact and transcripts are stored in SQLite.
Akou's temporary job retention (seven days) does not remove transcripts already
stored in Telegram Archive. Back up the archive independently as described above.

The initial pilot submits exactly five distinct downloaded voices using the
archive's own transcription client and event reconciliation, with automatic
collection disabled during the pilot. It checks successful non-empty database
results and unchanged audio hashes. Language labels and technical success are
not a measured word-error rate: review samples against their audio before treating
transcripts as exact quotations.

Pilot verification on 2026-10-29: five distinct voice files (about 70 seconds total)
produced five non-empty stored transcripts in 36.9 seconds, with original audio
hashes unchanged. All five were retrieved through the authenticated public viewer.
All output text was English; Dutch recognition and listening-based word accuracy
remain unverified. Akou, backup and viewer health checks passed after enabling
automatic voice-only transcription.
