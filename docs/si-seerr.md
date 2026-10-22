# Seerr on si

Seerr provides Plex media requests at https://request.type.hk. The managed Compose
service uses `ghcr.io/seerr-team/seerr:latest`, with persistent state in
`/mnt/storage/meta/appData/seerr`. Only nginx can access its host port
(`127.0.0.1:5055`). The nginx vhost is managed in chezetc; Cloudflare DNS must
contain a proxied CNAME `request.type.hk` → `type.hk`, matching the deployed DNS
record. nginx selects Seerr using the original `request.type.hk` hostname.
Existing origin TLS and authenticated origin pulls remain enabled.

Public HTTPS was verified on October 22, 2026: the root URL redirects to Seerr's
login page through Cloudflare. The container is healthy; Plex library scanning
and authenticated Sonarr/Radarr connection tests passed during setup.

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
| Radarr | `radarr:7878` | `4K:3 Balanced` (ID 19) | `/data/public/movies` | https://movies.type.hk |
| Sonarr | `sonarr:8989` | `HD:4 Balanced` (ID 16) | `/data/public/shows` | https://shows.type.hk |

Tautulli connects directly over the shared Docker network: hostname `tautulli`,
port `8181`, SSL disabled, and URL base empty. Its external URL is
`https://monitor.type.hk`. The public HTTPS endpoint uses port `443`; do not
combine the public HTTPS hostname with the internal HTTP port. The supported
Seerr save endpoint successfully tested this local connection on October 22.

In Seerr 3.5.1, advanced profile selection applies to new and pending requests.
Already-downloaded movies do not expose an in-place profile change: Seerr's
Radarr adapter returns an existing movie with a file without updating its profile.
Use the movie's cog menu → **Open in Radarr** → **Edit → Quality Profile**, then
save. Run **Search** in Radarr afterward to look for an upgrade immediately;
changing the profile alone does not start a backlog search.

Telegram uses the existing `@starprowlarr_bot` and the same chat as Prowlarr.
The enabled native agent embeds posters and sends silently. All request lifecycle
and issue events shown in Seerr's notification settings are enabled. The topic
field is empty for the existing private chat. Its bot token and chat ID are
restorable from Bitwarden Secrets Manager, `dotfiles` / `si-prowlarr-telegram`:
map `bot_token` to Bot Authorization Token and `chat_id` to Chat ID. Bot Username
is `starprowlarr_bot`. Credentials remain in application state and encrypted
backups, outside Git. A native Seerr test notification was delivered on October 22.

The curated defaults above are active; the movie default was already selected
before the legacy migration and was preserved. Anime also uses `HD:4 Balanced`
(Sonarr profile 16). Legacy service defaults and saved request-profile references were
migrated using the same approved map as the Arr libraries. See
[Profilarr](si-profilarr.md) for the 12 profiles, native resolution guards and
profile-migration procedure. All legacy profiles have been removed from Arr.

Service keys and Plex authentication belong in application state and Bitwarden,
never Git. The generated key is saved as `si-seerr-api-key` in the Bitwarden
Secrets Manager `dotfiles` project. Seerr settings and its SQLite database are
included in the existing encrypted daily appData backups and fi offsite copies. Rebuildable Seerr logs and
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
