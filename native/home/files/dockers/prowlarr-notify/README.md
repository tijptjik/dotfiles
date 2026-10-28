# Prowlarr Telegram formatting

Prowlarr's supported Custom Script connection calls
`/config/notifications/telegram.sh`. It uses Bash, jq and curl already present in
the image. No sidecar, image change or container restart is needed.

The server-only chezmoi hook deploys these two files into the existing Prowlarr
appData mount. It preserves credentials and does not edit notification settings
or send messages during apply. Client hosts skip the hook and Docker sources.

Private configuration is `/config/notifications/telegram.json` inside the
container (host: `/mnt/storage/meta/appData/prowlarr/notifications/telegram.json`).
It contains `bot_token`, `chat_id`, optional `topic_id`, and `send_silently`.
Keep it mode 0600, owned by Prowlarr's runtime UID; never add it to Git. It is
included in encrypted application backups and saved in Bitwarden Secrets Manager,
project `dotfiles`, key `si-prowlarr-telegram`.

The existing connection retains its Grab and Application Update event selections,
same bot/chat and silent delivery. Test verifies the Telegram destination without
sending a message. Grab messages show title/episode or movie year, episode title,
resolution/source/codec/HDR, app, indexer and size. Metadata is HTML-escaped.
Unusual titles fall back to a readable release title. Full release data remains in
Prowlarr's history. Health-event rendering is supported, but those events remain
disabled unless explicitly selected later.

For an offline preview, set `PROWLARR_TELEGRAM_DRY_RUN=1` and supply the documented
`prowlarr_*` custom-script environment variables. This emits an unsigned message
payload without reading credentials. `prowlarr_telegram_preview=1` labels a live
preview as an already-grabbed release; it never initiates acquisition.
