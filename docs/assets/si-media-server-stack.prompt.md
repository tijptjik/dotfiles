# si media server stack — generation prompt

Generator: built-in image_gen tool, image edit mode.
Final artwork: si-media-server-stack.png.
Updated: 22 October 2026.

References:
1. Original stack poster: /home/io/.codex/generated_images/01a15e63-7c0e-74e1-b3e8-bed89b903ff8/exec-ef58f314-d1e3-4fc9-9b30-3d3e9eb6edec.png
2. Seerr official logo: https://raw.githubusercontent.com/seerr-team/seerr/564bfb08b54caa374bddaf820abfd226e5e69151/public/os_logo_filled.png
3. Profilarr official logo: src/lib/client/assets/logo-512.png from the reviewed Profilarr source checkout.

Configuration references: docs/si-seerr.md, docs/si-profilarr.md,
docs/si-application-backups.md and native/home/files/dockers/docker-compose.yaml.j2.
The poster describes the configured stack, not a live health report.

## Exact prompt

Edit target: reference image 1, the existing tall white "si — Media server stack" poster. Reference image 2 is the official Seerr icon only. Reference image 3 is the official Profilarr icon only. Recreate the existing stack poster with the two added services below, retaining its clean white background, black Helvetica-like typography, thin rules, colorful service icons, blue storage wiring, three columns GET / SERVE / UTIL, and lower RUNTIME / SHARED STORAGE / APPLICATION RECOVERY sections. This is an updated version of the same poster, not a new aesthetic. Portrait layout roughly 1:2. Use high resolution and crisp, accurate lettering. Increase the height of the service area as needed so no text is compressed, clipped or crowded.

Mandatory additions:
1. In GET, add Seerr as the FIRST service, using the actual Seerr icon from reference 2. Text: "Seerr"; description: "Movie & TV requests"; small URL: "request.type.hk".
2. In UTIL, add Profilarr as the FIRST service, using the blue-gray two-arrow official Profilarr icon from reference 3. Text: "Profilarr"; description: "Quality profile policy"; small URL: "profiles.type.hk". Profilarr's sync is manual; do not imply it performs downloads or unattended bulk upgrades.
3. In the Connections block add "Seerr → Radarr + Sonarr", "Plex → Seerr availability", and "Profilarr → Radarr + Sonarr · manual". Retain the three existing connections. The connections must be readable and clearly separated; short lines may wrap.

Exact complete services in each column, in this order:
GET:
Seerr — Movie & TV requests — request.type.hk
Radarr — Movies
Sonarr — TV series
Lidarr — Music acquisition
Bookshelf — Ebook automation
Shelfmark — Book requests
LazyLibrarian — Books & magazines
Ephemera — Book discovery
Transmission — Torrent downloads

SERVE:
Plex — Movies & TV
Grimmory — Ebook library
Audiobookshelf — Audiobooks & podcasts
Navidrome — Music library
Feishin — Music player
Octo-Fiestarr — On-demand music proxy
Connections:
Seerr → Radarr + Sonarr
Plex → Seerr availability
Profilarr → Radarr + Sonarr · manual
Feishin → Navidrome
Grimmory → MariaDB
Plex → Tautulli → Plex Rewind

UTIL:
Profilarr — Quality profile policy — profiles.type.hk
Prowlarr — Indexer management
Unpackerr — Archive extraction
Beets — Music tags & imports
Beets Audible — Audiobook tags & imports
Auto-M4B — Audiobook conversion · manual
Byparr — Challenge solving
FlareSolverr — Browser challenge proxy
Tautulli — Plex activity
Plex Rewind — Viewing highlights

Preserve the original lower technical diagram:
RUNTIME: Docker Compose — app containers; MariaDB — Grimmory database; Native systemd — Plex + scheduled jobs; Fedora 45 — host operating system.
SHARED STORAGE: /public — Media libraries; /meta — App data, cache & downloads — Excluded from SnapRAID. Both connect to "mergerfs · /mnt/storage". Separate dotted callout "/appData/mariadb — Host-side database files".
DATA · ext4 · 64 TB nominal: five data disks d1 / disk12 — 8 TB; d2 / disk22 — 16 TB; d3 / disk32 — 8 TB; d4 / disk42 — 16 TB; d5 / disk5 — 16 TB. Mounts: /mnt/data/<disk>.
SnapRAID: Two parity disks · outside the pool. P1 / disk12 — 16 TB; P2 / disk22 — 16 TB. Mounts: /mnt/parity/<disk>. Dashed data-to-parity arrows.
Below: "Sync: daily 05:00 · Scrub: Sunday 08:00, 25% · HKT". Followed by "Scheduled parity protects synced media; it is not a backup."
APPLICATION RECOVERY: "App configs + consistent DB exports" → "Restic · si" → "Independent copy · fi".
Update the outdated backup footer to the verified current coverage, with these three readable lines:
"Daily 04:00 on si · Weekly Sunday 06:00 pull by fi · HKT"
"fi checks daily 10:00 · 7 daily + 4 weekly restore points"
"App state + /public/library · Other media/downloads excluded"
Small bottom-right caption: "Configured stack · October 2026".

Keep the large lowercase "si" title and "Media server stack" subtitle at the top left, and Fedora 45 wordmark and icon at top right. Preserve other service icon identities from the original. Render each service exactly once; no duplicate rows, omitted services, invented new services, or crossed-out placeholders. No credentials, no user names, no private documents section. Prioritize correct service labels, clear grouping and clean visual hierarchy.

