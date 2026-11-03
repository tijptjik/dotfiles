# Bitwarden secret names

Use `UPPER_SNAKE_CASE` for operational secrets in the `dotfiles` project:
`[SCOPE_]SERVICE_PURPOSE_TYPE`. Scope identifies a host or application when the
credential is specific to it. Keep established service names such as `ZAI` and
`RUNTJIK`. Use `API_KEY`, `API_SECRET`, `CLIENT_SECRET`, `PASSWORD`, or `TOKEN`
for individual values, `CONFIG` for configuration bundles, `CREDENTIALS` for
mixed login credentials, and `RECOVERY_KEYS` for recovery documents.

These are Bitwarden display names. Runtime environment variable names are
application contracts and need not match them. Consumers must resolve secrets
by UUID. Rename an existing entry in place; do not recreate it, rotate its value,
move projects, or change its notes as part of a naming cleanup.

## Naming review, 2026-11-03

The table covers the twelve named screenshot entries, including the follow-up
screenshot, the matching AMO API key, and two subsequently requested storage
credential renames.
Names and UUIDs were checked against live Bitwarden metadata. Usage was traced
through Dotjik and the local TjikOS source. Other projects, untracked external
automation, and deployed application settings have not been exhaustively audited.

Status: twelve entries renamed and read back successfully on 2026-11-03; three
names already matched the convention. Every entry's other fields were compared
in memory and preserved, excluding Bitwarden's revision timestamp. No secret
values were printed or saved. Other vault entries were not renamed in this pass.

| Previous name | Canonical name | Consumer or recovery purpose |
| --- | --- | --- |
| `RUNTJIK_AMO_API_KEY` | unchanged | Fi's `~/.config/runtjik/amo.env`, exported as `WEB_EXT_API_KEY` for Mozilla extension signing. |
| `RUNTJIK_AMO_API_SECRET` | unchanged | Same file, exported as `WEB_EXT_API_SECRET`. |
| `si-app-backup-recovery-keys` | `SI_APP_BACKUP_RECOVERY_KEYS` | Recovery document containing Si and Fi application-backup repository passwords and instructions; manual recovery, no managed name lookup found. |
| `si-lazylibrarian-api-key` | `SI_LAZYLIBRARIAN_API_KEY` | LazyLibrarian/Prowlarr integration; restored through application state or manual recovery. |
| `si-profilarr` | `SI_PROFILARR_CREDENTIALS` | Profilarr administrator password and runtime API key; application state and `runtime.env` recovery. |
| `si-prowlarr-telegram` | `SI_PROWLARR_TELEGRAM_CONFIG` | Bot token/chat configuration shared by Prowlarr and Seerr; manual recovery to application configuration. |
| `si-seerr-api-key` | `SI_SEERR_API_KEY` | Seerr API credential; application-state/manual recovery. |
| `si-snapraid-telegram` | `SI_SNAPRAID_TELEGRAM_CONFIG` | Recovery of root-only `/etc/si-notifications/telegram.json` for Synctjik notifications. |
| `SPOTIFY_SECRET` | `SPOTIFY_CLIENT_SECRET` | Navidrome's `ND_SPOTIFY_SECRET`, rendered from the same UUID in managed Compose. |
| `tjikup-telegram` | `TJIKUP_TELEGRAM_CONFIG` | Tjikup scheduled-report destination JSON, resolved through `bws_secret_id`. |
| `ZAI_API_KEY` | unchanged | Client Fish `ZAI_API_KEY`; also supplies `ANTHROPIC_API_KEY` when the selected provider is Z.ai. |
| `tijkapp-telegram-bot-token` | `TIJKAPP_TELEGRAM_BOT_TOKEN` | Telegram bot token by its existing label; no direct name or UUID reference found in the checked source. Consumer remains unverified. |
| `TIJPTJIK_PUBLIC_PASSWORD` | `PUBLIC_PASSWORD` | Transmission's `PASS` value in managed Compose, resolved by UUID; other potential consumers were not verified. |
| `PRIVATE_RESTIC_PASSWORD` | `SYNCTIJK_RESTIC_PRIVATE_PASSWORD` | Private-storage Restic backups and Si's Drive archive backups; managed password templates resolve the same UUID. |
| `RCLONE_CRYPT_RECOVERY_CONFIG` | `SYNCTIJK_RCLONE_CRYPT_RECOVERY_CONFIG` | Synctjik crypt recovery through `crypt_secret_id` in managed private-storage configuration. |

The Tjikup entry's live name used a hyphen at review time, not an underscore.
Prowlarr's Telegram configuration is shared with Seerr; its name retains the
original bot owner rather than implying a separate Seerr credential.
The `TIJKAPP` spelling is preserved from the existing entry; it was not silently
corrected to another application name. `PUBLIC_PASSWORD` is the explicitly
requested name; the source reference does not establish that Transmission is
its only consumer.
The `SYNCTIJK` prefix preserves the explicitly requested spelling of these
Bitwarden labels; the application and executable remain named Synctjik/`synctjik`.

## Stable identities

| Canonical name | UUID | Source of usage evidence |
| --- | --- | --- |
| `RUNTJIK_AMO_API_KEY` | `07fe4f15-e928-4a06-8393-b4f4005b7a80` | `native/home/templates/runtjik/amo.env.j2` |
| `RUNTJIK_AMO_API_SECRET` | `38fb1d03-d2af-4e7d-aa4c-b4f4005b7b7a` | `native/home/templates/runtjik/amo.env.j2` |
| `SI_APP_BACKUP_RECOVERY_KEYS` | `47f541ff-8452-46ae-92a3-b4ea010abdfb` | [Application-backup recovery](si-application-backups.md#user-recovery-key-handoff) |
| `SI_LAZYLIBRARIAN_API_KEY` | `760439c1-fce7-449c-a434-b4ea01125957` | [Media automation](si-media-automation.md) |
| `SI_PROFILARR_CREDENTIALS` | `b95e29eb-8d92-43f4-ae32-b4eb003aee99` | [Profilarr](si-profilarr.md) |
| `SI_PROWLARR_TELEGRAM_CONFIG` | `681aa67b-ac20-405c-82df-b4ea0131f417` | [Seerr](si-seerr.md) and `native/home/files/dockers/prowlarr-notify/README.md` |
| `SI_SEERR_API_KEY` | `213ba8b2-48c8-4e2b-97eb-b4eb0024f766` | [Seerr](si-seerr.md) |
| `SI_SNAPRAID_TELEGRAM_CONFIG` | `35e17db5-b9b4-4f3d-9049-b4ea0123e34d` | [SnapRAID notifications](si-snapraid-maintenance.md) |
| `SPOTIFY_CLIENT_SECRET` | `29598444-cf58-448d-a7bf-b3d7008a937f` | `native/home/files/dockers/docker-compose.yaml.j2`, Navidrome |
| `TJIKUP_TELEGRAM_CONFIG` | `b48c676a-7771-4ae9-b3a2-b4f20124969b` | `native/home/files/.config/tjikup/telegram.json.j2` |
| `ZAI_API_KEY` | `eb869167-2cd3-4d14-aa8b-b3b0008ce9e3` | `native/home/templates/fish/conf.d/secrets.fish.j2` |
| `TIJKAPP_TELEGRAM_BOT_TOKEN` | `b3fcf113-c1b6-4a2e-9879-b4f201237f2f` | Live Bitwarden identity verified; direct source consumer not found. |
| `PUBLIC_PASSWORD` | `d0001509-175f-4cef-9ca6-b3cb00abff89` | `native/home/files/dockers/docker-compose.yaml.j2`, Transmission |
| `SYNCTIJK_RESTIC_PRIVATE_PASSWORD` | `90f34958-6254-4b0c-bc65-b4ed0026bee2` | `native/home/templates/private-storage/restic-password.j2` and `native/home/templates/drive-restic/restic-password.j2` |
| `SYNCTIJK_RCLONE_CRYPT_RECOVERY_CONFIG` | `061503b8-30bd-4f98-8cdb-b4ed0026bdc1` | `native/home/files/.config/private-storage/config.json`, `crypt_secret_id` |

TjikOS's `apps/tjikup/src/managed_files/secrets.rs` calls `bws secret get` with
the UUID. Its `scheduled.rs` resolves Telegram through the same provider. The
managed consumers therefore do not need a deployment or cache refresh for a
display-name change. Recovery runbooks must follow the new names.

## Rename verification

Before editing, check each UUID, old name, project, and target-name uniqueness.
Use `bws secret edit UUID --key NEW_NAME`, supplying the access token through
the existing private environment, never on the command line. Capture CLI output
privately because it can include secret values. Read back each entry and compare
the UUID, value, note, organization, and project with its pre-edit state in memory;
only the name and service-maintained revision fields should change. Do not store
plaintext snapshots or values in Git or validation logs.

Repository validation uses synthetic secrets and separate Fi, Li, and Si fixture
homes. It does not prove that deployed services or recovery workflows work live.
Do not send Telegram test messages or restart services to verify a label change.

`bash scripts/validate.sh` passed during this review: 363 tests, nine skipped,
including separate host fixtures. Live validation covered Bitwarden rename and
read-back only; application behavior and recovery were not exercised live.
