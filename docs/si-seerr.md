# Seerr on si

Seerr provides Plex media requests at https://request.type.hk. The managed Compose
service uses `ghcr.io/seerr-team/seerr:latest`, with persistent state in
`/mnt/storage/meta/appData/seerr`. Only nginx can access its host port
(`127.0.0.1:5055`). The nginx vhost is managed in chezetc; Cloudflare DNS must
contain a proxied CNAME `request.type.hk` → `indexer.type.hk`, which follows the
existing media-service origin.
Existing origin TLS and authenticated origin pulls remain enabled.

## Application setup

Use the existing Plex owner account to complete initial setup before publishing
DNS. Set the application URL to `https://request.type.hk` and enable reverse-proxy
trust. Connect Plex through `host.docker.internal:32400`, enable the movie and
television libraries, and scan availability. Do not import Plex users automatically.
New users require approval for requests; automatic approval and watchlist requests
are not enabled by this setup.

Configure the default non-4K services as follows:

| Service | Internal address | Quality profile | Root folder | External URL |
| --- | --- | --- | --- | --- |
| Radarr | `radarr:7878` | `2. HD - High` (ID 4, 1080p) | `/data/public/movies` | https://movies.type.hk |
| Sonarr | `sonarr:8989` | `1080p Only` (ID 9) | `/data/public/shows` | https://shows.type.hk |

Service keys and Plex authentication belong in application state and Bitwarden,
never Git. The generated key is saved as `si-seerr-api-key` in the Bitwarden
Secrets Manager `dotfiles` project. Seerr settings and its SQLite database are included in the existing
encrypted daily appData backups and fi offsite copies. Rebuildable Seerr logs and
cache are excluded. The application is paused alongside the other acquisition
services during guarded SnapRAID maintenance.

## Deploy and restore

Provision the managed Seerr directory only after the storage guard passes. The
image runs as UID 1000; the directory manifest grants UID 1000/GID 950 access.
From `/home/m/dockers`, use `docker compose pull seerr` and
`docker compose up -d --no-deps seerr`. Updates follow the same commands; the
image is deliberately not pinned beyond the Compose tag.

For replacement-host recovery, restore the Seerr appData directory from the
normal encrypted application backup before starting its container. Preserve the
restored owner and keys; do not complete a new setup wizard over a restored
configuration. Confirm the health check, Plex library scan, Radarr/Sonarr
connection tests and public HTTPS login after startup.

```sh
sudo docker inspect --format '{{.State.Health.Status}}' seerr
curl --fail http://127.0.0.1:5055/api/v1/status
sudo nginx -t
```
