# Homepage and Scrutiny on Si

Both services run in the existing `dockers` Compose project with persistent state
under `/mnt/storage/meta/appData`. Only these two containers are started or
recreated during their deployment.

## Access

The requested public routes are https://home.type.hk (Homepage) and
https://storage.type.hk (Scrutiny). They have not been activated: explicit
approval of unauthenticated public access or a login protection choice is pending.
Both hostnames currently reach nginx's default page. The dashboard links and
four-column layout are prepared for the requested domains.

Both Docker host ports remain loopback-only. Access the running dashboards
through an SSH tunnel:

```sh
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:3000:127.0.0.1:3000 \
  -L 127.0.0.1:8085:127.0.0.1:8085 m@ssh.type.hk
```

Open http://localhost:3000 or http://localhost:8085 while the tunnel runs.
Until the public route is activated, open Scrutiny directly through the tunnel;
the new Storage link targets the pending public hostname.

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
