#!/bin/bash
# Prowlarr Custom Script connection. Secrets stay in backed-up appData.
set -euo pipefail
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
config=${PROWLARR_TELEGRAM_CONFIG:-/config/notifications/telegram.json}
event=${prowlarr_eventtype:-${Prowlarr_EventType:-}}
if [[ -z "$event" ]]; then
    echo 'Missing Prowlarr notification event' >&2
    exit 1
fi

if [[ "${event,,}" == test ]]; then
    # Prowlarr tests run this branch. Verify the destination without chat spam.
    method=getChat
    payload='{}'
else
    method=sendMessage
    payload=$(jq -n 'env' | jq -f "$script_dir/format.jq")
fi

if [[ ${PROWLARR_TELEGRAM_DRY_RUN:-0} == 1 ]]; then
    printf '%s\n' "$payload"
    exit 0
fi
if [[ ! -r "$config" ]]; then
    echo 'Restore /config/notifications/telegram.json from Bitwarden or the encrypted app backup' >&2
    exit 1
fi
# Build curl configuration on stdin: bot token and chat ID never enter argv or logs.
response=$(jq -rn --slurpfile secret "$config" --arg method "$method" --argjson payload "$payload" '
  $secret[0] as $s |
  ($payload + {chat_id:$s.chat_id} +
   (if $method == "sendMessage" then
      {disable_notification:($s.send_silently // true)} +
      (if ($s.topic_id // "") != "" then {message_thread_id:$s.topic_id} else {} end)
    else {} end)) as $body |
  "url = " + ("https://api.telegram.org/bot" + $s.bot_token + "/" + $method | @json),
  "request = \"POST\"",
  "header = \"Content-Type: application/json\"",
  "data = " + ($body | tojson | @json)
' | curl --config - --silent --show-error --fail --connect-timeout 10 --max-time 30)
if ! jq -e '.ok == true' <<<"$response" >/dev/null; then
    echo 'Telegram rejected the notification' >&2
    exit 1
fi
if [[ "$method" == sendMessage ]]; then
    printf 'Telegram notification sent; message %s\n' "$(jq -r '.result.message_id' <<<"$response")"
else
    echo 'Telegram destination verified'
fi
