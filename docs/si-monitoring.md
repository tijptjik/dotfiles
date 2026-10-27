# Homepage and Scrutiny on Si

Both services run in the existing `dockers` Compose project with persistent state
under `/mnt/storage/meta/appData`. Only these two containers are started or
recreated during their deployment.

## Access

Homepage is served at https://home.type.hk and Scrutiny at
https://storage.type.hk through nginx and Cloudflare. The user explicitly
approved public access without login protection. These routes expose the
dashboard links, disk summary, and Scrutiny disk details and web controls.
The vhosts are managed in chezetc's `type.hk` nginx configuration.
Homepage allows `home.type.hk` as well as the existing localhost hosts.

Both Docker host ports remain loopback-only. Access the running dashboards
through an SSH tunnel:

```sh
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:3000:127.0.0.1:3000 \
  -L 127.0.0.1:8085:127.0.0.1:8085 m@ssh.type.hk
```

Open http://localhost:3000 or http://localhost:8085 while the tunnel runs.
The Storage link targets https://storage.type.hk.

## Configuration and deployment

The Compose template and port definitions are managed by chezmoi.
`home/dockers/homepage/*.yaml` are versioned starter configuration files; the
running app reads its writable copy in `/mnt/storage/meta/appData/homepage`.
When changing dashboard configuration, update the source and copy the selected
YAML files into the appData directory on Si. Avoid overwriting runtime changes
without comparing them first. No Docker socket or application API keys are
needed for the current dashboard. The Scrutiny widget uses the private Docker
network endpoint `http://scrutiny:8080`.

For initial provisioning, after the Compose file has been rendered to
`/home/m/dockers/docker-compose.yaml`:

```sh
sudo python3 /etc/si-provision/storage.py --check
sudo install -d -o 1000 -g 950 -m 0750 /mnt/storage/meta/appData/homepage
sudo install -d -m 0750 /mnt/storage/meta/appData/scrutiny/config \
  /mnt/storage/meta/appData/scrutiny/influxdb
cp /home/m/.local/share/chezmoi/home/dockers/homepage/*.yaml \
  /mnt/storage/meta/appData/homepage/
cd /home/m/dockers
docker compose config --quiet
docker compose pull homepage scrutiny
docker compose up -d --no-deps homepage scrutiny
```

Use the final three commands for image updates, reviewing release notes first.
Both containers restart automatically. Images follow upstream `latest` and
`latest-omnibus` tags; no automatic updater was installed.

## Disk collection

Scrutiny's omnibus container includes its API, collector and InfluxDB. Only the
web port is published; InfluxDB remains internal. SMART is collected at startup
and daily at 06:00 Asia/Hong_Kong. No self-tests or disk writes are scheduled.
The container has `SYS_RAWIO`, read access to `/dev/sda` through `/dev/sdh`, and
read-only udev metadata. It does not use privileged mode or `SYS_ADMIN`.

Those eight paths cover all current physical disks, including the OS SSD.
Scrutiny records serial/WWN identities; disk letters are not persistent identity.
Recheck `lsblk` and the Compose device list after adding/removing disks and
recreate the container to refresh device mappings. Confirm all expected serials
have recent SMART samples, rather than trusting discovery counts alone.

```sh
docker exec scrutiny /opt/scrutiny/bin/scrutiny-collector-metrics run
curl --fail http://127.0.0.1:8085/api/health
curl --fail http://127.0.0.1:8085/api/summary
curl --fail http://127.0.0.1:3000/api/healthcheck
```

Notifications are not configured. The dashboard displays findings; external
alert delivery requires separate notification configuration.

The existing application backup job includes appData and exports SQLite files.
It does not provide a verified native InfluxDB backup: treat Scrutiny time-series
history as rebuildable until a native export/restore workflow is added. Homepage
configuration is also preserved in this repository.

## Rollback

Stop and remove only the two new containers with
`docker compose stop homepage scrutiny` and
`docker compose rm -f homepage scrutiny`. Retain their appData directories.
Remove their service definitions and ports from the managed configuration if
retiring them permanently. Do not run `docker compose down` for the shared stack.

## Installation verification — October 22, 2026

Homepage v2.6.0 and Scrutiny v0.9.5 loaded successfully through the SSH tunnel.
Homepage's live Scrutiny widget returned data. Both health endpoints passed,
and every one of the eight discovered serials had a timestamped SMART sample.
The initial collection completed at 16:13 HKT. The existing media containers
were not recreated.

The 8 TB Seagate `WSD33L2N` (currently `/dev/sdc`, DISK32) returned smartctl
exit status 32: a historical attribute-threshold breach, specifically airflow
temperature. Its overall SMART status currently passes; reallocated, pending
and offline-uncorrectable sector counts are all zero. Its temperature was 50°C
at verification, with a recorded lifetime maximum of 68°C. Scrutiny's generic
"close to failure" collector log should not be mistaken for a current overall
SMART failure. Review cooling and future trends; no disk settings were changed.

## Homepage service availability

All thirteen service cards use Homepage's native `siteMonitor` with internal URLs.
Checks refresh every 30 seconds while the page is open; the UP/DOWN label's
hover text includes HTTP status and latency. This is HTTP availability, not
continuous alerting or complete functional validation. Native health/status/ping
endpoints are used where available. Feishin checks its web root; Transmission
returns HTTP 401, which Homepage explicitly treats as a reachable authenticated
service. Homepage does not interpret health-response JSON or test downloads,
playback, authentication, or external Cloudflare routes. Plex uses `http://host.docker.internal:32400/identity`; the user explicitly
approved Homepage container-to-host access through Docker's host-gateway mapping.
The Community footer uses the Telegram icon and retains its 400px maximum width.

Homepage configuration assets under `/api/config/` are served with
`Cache-Control: no-store`. Cloudflare previously cached a zero-byte custom.css
response, which hid the footer styling. The exact CSS URL was purged after
adding the no-store header. Community is capped at 400px with 2rem top padding.

## Rose Punk server icons — deployed October 28, 2026

The source configuration uses `/images/rose-punk/*.svg` for all thirteen services
and the Community link. The fourteen frameless icons and the refreshed StarFix
design were deployed to Si on October 28, 2026. The title and favicon remain.

Rebuild the served SVGs offline:

```sh
python3 scripts/icons/homepage.py
python3 -B -m unittest discover -s tests -p 'test_homepage_icons.py' -v
```

The builder requires Python, PyGObject/librsvg, pycairo and Pillow. It reads only
editable SVGs and `scripts/icons/homepage.json`; source hashes are verified
before any output is written. Its outputs belong under
`home/dockers/homepage/images/rose-punk/`. It generates no galleries, screenshots
or before/after assets. No desktop-theme rebuild or local review archive is
needed. Source URLs, reference hashes, attribution and licences remain with the
manifest and `scripts/icons/homepage-upstream/`.

Plex, Transmission, Prowlarr and Telegram use the same editable sources as the
desktop set in `scripts/icons/local/`. The ten service-specific sources live
under `local/homepage/`. All share optical sizing on a transparent 64 × 64 grid;
app-specific borders and backings remain part of the artwork.

The finished service set includes a Hong Kong-centred Plex globe, a matte violet
Seerr iris, a lavender grimoire, books with headphones, a mint record player,
paired radar/sonar screens, a ribbon bookmark, five adult figures and rose
monitoring glasses. The latest pass clarifies instrument markings, makes the
figures' faces more natural and harmonises the rose accents.

All icon comparison galleries, historical snapshots, original-image review
copies and rendered previews are archived under ignored `.local/icon-reviews/`.
They remain available on this checkout but are excluded from commits and are not
production build inputs. Canonical editable SVGs and served assets remain in
the repository.

For subsequent deployments, compare and back up the runtime files first, then copy the
reviewed `services.yaml`, `bookmarks.yaml`, `custom.css`, and `images/rose-punk/`
into `/mnt/storage/meta/appData/homepage`. The existing read-only
`/app/public/images` mount serves this directory. Preserve other runtime
configuration and services. After deployment, verify all fourteen SVG URLs,
desktop/mobile layout, thirteen service monitors and Scrutiny metrics.

## StarFix design refresh — October 28, 2026

The deployed CSS gives the illustrations more space, replaces the dark icon
backings with transparent canvases, and uses a warm ivory wordmark with a short
media subtitle. Rose, cyan, lavender and amber rules distinguish the four
sections. Cards use restrained plum surfaces, stronger names, quieter live
status labels and a shared metrics strip. The Community link remains centred
with a 400px group cap and 2rem top padding. Layout uses one, two or four columns;
hover movement respects reduced-motion settings.

The deployment changed only `services.yaml`, `bookmarks.yaml`, `custom.css` and
the fourteen SVGs in the running Homepage appData directory. Settings, service
links, monitor URLs and widget definitions were compared with the live files
before the update; functional configuration matched after excluding icon paths.
The image mount already existed, so no Compose changes or image updates were
needed. `docker restart homepage` refreshed assets after installation. All other
containers retained their IDs and start times.

Backup and receipt:
`/mnt/storage/meta/appData/homepage-backups/20261027T173128Z/`.
`runtime-before.tar.gz` contains the previous four configuration files and
images. Every archived file passed SHA-256 readback against its original before
installation. The folder also retains the Compose file, before/after container
inventories, installation hashes and `receipt.json`. To roll back the site,
restore the runtime archive into the Homepage appData directory and restart only
Homepage; retained new SVGs are harmless when the old config no longer uses them.

Fresh browser verification on `https://home.type.hk` confirmed all fourteen SVGs
returned HTTP 200 with the deployed hashes. The public stylesheet also matched,
with Cloudflare `BYPASS` and `Cache-Control: no-store`. All thirteen monitors
reported UP (Transmission's authenticated HTTP 401 is expected), and Scrutiny
showed 8 passed, 0 failed and 0 unknown. Browser checks at 320, 390, 800 and 1568px
found no horizontal overflow or clipped cards; section collapse/expand, centred
Community and reduced-motion behaviour also passed. No console errors were seen.
