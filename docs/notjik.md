# Desktop notifications

[Notjik](https://github.com/tijptjik/tooltjik/tree/main/apps/notjik) is the
Quickshell notification server. Its source, tests and rose-punk demo live in the
tooltjik monorepo under `apps/notjik`.

On desktop clients (`fi` and `li`), `chezmoi apply` builds and installs Notjik
from a shared tooltjik checkout. Both installers bootstrap it independently when
absent, using `~/code/tooltjik` on every host. Set `TOOLTJIK_REPO` to select
another checkout. Existing checkouts are never pulled by installers; update
them before applying. Older `~/.local/share/tooltjik` checkouts must be moved
first; see the migration instructions in [Tjikup](tjikup.md).

Notjik is enabled for graphical sessions and started when a
session is active; an already running instance is not restarted, preserving
in-flight replies and recordings. Server `si` skips this desktop hook and config.

For a manual installation from the tooltjik checkout:

```sh
bun run --filter @tooltjik/notjik build
bash scripts/install.sh notjik
systemctl --user daemon-reload
systemctl --user enable --now notjik.service
```

The installer supplies the user service and standard D-Bus activation entry.
Quickshell, Python 3 and Qt's GraphicalEffects module (`qt6-qt5compat` on Fedora)
are runtime dependencies. The managed desktop service
uses the same `qt6ct` platform theme as the shell, so named sender icons resolve
consistently; its override lives in `notjik.service.d/theme.conf`. Only one desktop notification
server can own `org.freedesktop.Notifications`.

Chezmoi manages `~/.config/notjik/config.json`, Hyprland bindings, the Bartjik DND
control and notification activation. Keep the JSON template in expanded two-space
format and preserve its key order when editing: Chezmoi compares file bytes, so
formatting-only rewrites of the live config can cause overwrite prompts. The client default is rose-punk, bottom
centre on the primary display (`DP-1` on fi, `eDP-1` on li). If that connector is
absent, the first connected screen is used. Set `placement.monitors` to `all` or
an array of connector names/indexes to override this. Settled cards are opaque;
all visible cards stay full-size; only dismissed or expired cards shrink and fade out. Lock-screen presentation is
hidden by default. Low urgency uses muted text/artwork, normal uses neutral white,
and critical uses rose-pink. Lists have extra separation from surrounding paragraphs;
sender text stays literal. `stack.animationMs` (default 220ms) controls the motion
response. Bursts share one continuous upward movement: card heights determine
when the next card enters, with no fixed stagger or restart between pushes.
The first card appears at the bottom before the stack moves; departing cards recede and
fall behind the remaining stack. Wireless
notifications use the painted sci-fi communications dish; the default fallback is a matching robot portrait. Both stay in full colour, in an 80 px strip flush with the left edge and cropped to the full card height. Sender icons and Telegram avatars remain inset; supplied images still take priority.

Kitty reports use the robot portraits instead of Kitty's supplied terminal image.
Default robot artwork is drawn from the notification's urgency: 64 attentive
portraits for `normal`, 12 red-alert portraits for `critical`, and 12 dreaming
portraits for `low`. The draw stays stable during updates and in history; changing
urgency selects from the new set. Older history gets a deterministic choice from
the appropriate set without rewriting archived records. Artwork and generation
prompts live in tooltjik's `apps/notjik/qml/icons/robots/manifest.json`.

Action sections collapse completely when idle. A thicker middle 30% of the
bottom border, in the same dim border colour, marks cards with interactions. Hover or keyboard selection slides
out their controls; moving away collapses them. Active replies and recordings
keep their controls open. This applies to ordinary actions and Telegram demos
as well as live Telegram cards.

Opening a native Telegram notification invokes its chat action, focuses the existing
Telegram window (revealing its workspace), and dismisses the notification.

- Super+M opens both Bartjik and history if either is closed, and closes both
  when both are open. The shortcut reads their live state so edge activation
  or dismissing history independently cannot invert the two panels. Bartjik stays open
  until Super+M is pressed again or the pointer reaches its activation edge.
  Edge contact restores normal auto-hide behavior. Bartjik uses native bottom-edge activation,
  stays open while its bar or panels are hovered, and hides after 1000 ms outside
  its 140px safe distance. Hyprland must not run a separate bar visibility timer.
- Super+comma / Super+period browse older/newer notices.
- In the focused history drawer, `/` opens a filter for titles, message text,
  app names and groups. Results update as you type, ignoring case; all typed
  words must match. Matching groups expand and navigation stays within results.
- Tab selects the next search result; Shift+Tab selects the previous one,
  wrapping at the ends. The search text stays editable.
- Escape clears an open filter first, then closes history on the next press,
  or releases notification keyboard focus outside history.
- Click the card background to dismiss; click an action button to run its action.
  Actions use quiet text buttons beneath a subtle divider; chevrons slide to additional buttons when they
  overflow. Long labels wrap inside their buttons; page changes keep the footer height steady.
  The primary action (native `default`, otherwise the first supplied action) sits
  on the right; secondary actions sit on the left. A lone action is right-aligned.
- ChatGPT's Open action also runs `show-codex` after delivering the native action,
  revealing and focusing its `special:codex` workspace on the window's monitor.
  An already visible workspace stays open. This requires the Notjik build with
  `actions.nativeHooks` support; hooks match the caller and native action identifier
  and execute a local command argument array without a shell.
- Drag any non-interactive part of a card to detach a regular floating window,
  including onto another monitor. It belongs to its Hyprland workspace and stays
  there when you switch workspaces. Clicking another window keeps detached cards
  above it without taking focus. Hold **Super** and left-drag anywhere on it to
  move it (**Super** + right-drag resizes it). Focus a card to use normal window shortcuts,
  including Super+Shift+number to send it to another workspace and the close
  shortcut to dismiss it. Drag it again to move it; **×** also dismisses it. Buttons,
  media controls and text editors keep their own gestures. Detached cards do not
  expire, and their background is safe to click. Sender updates continue in place;
  the sender can still close them. Other messages in a group stay in the stack.
  New arrivals and sender updates preserve its window and workspace. Hyprland
  handles monitor disconnection. Windows last for the current Notjik session.
  The `notjik-detached` window rule supplies their initial floating style and
  disables compositor blur/shadows during the transparent drop handoff;
  `notjik-floating` applies only to the initial drag preview.
- `actions.blacklist` disables all actions for listed callers, including keyboard
  and IPC invocation. The managed config blocks `telegram`, `Telegram Desktop`,
  `Mullvad VPN` and `mullvad-vpn`, covering Telegram's caller names and Mullvad's
  application name and desktop-entry ID. Entries match
  the application name or desktop-entry ID exactly, ignoring case and surrounding
  whitespace. Changes affect existing cards within about a second; use `[]` to
  allow every caller. Native actions use the Freedesktop notification standard.
- `notjikctl demo --solo` previews cards in the normal notification service.
- `notjikctl demo list` lists the available card types.
- `notjikctl demo telegram-grouped --solo` previews synthetic text, photo and
  voice messages as a group. Add `--log` to include the demo in history.
- `notjikctl demo robots --solo --interval 2s` previews the robot artwork.
- `notjikctl demo clear --solo` dismisses the demo cards.
- Recording and comparison demos are documented in
  [Tooltjik's demo guide](https://github.com/tijptjik/tooltjik/blob/main/apps/notjik/docs/comparison.md).
- `notjikctl logs` reads the persistent event history.
- `notjikctl status` reports pause and delivery state; `notjikctl resume` releases queued notices.

History starts with collapsed groups and compact timestamped rows. Selecting a
row shows its full details; archived actions cannot be replayed. The drawer and
selected popups use on-demand focus rather than exclusive desktop focus. A paused
service also shows a Resume button in history.

Grouped popups keep their right-edge notches visible even when hover-only action
controls are hidden. They use notches at fixed 10 px spacing, vertically centred, instead of a text count, one
per message up to five. Hover anywhere on the grouped card for 400 ms or click its notch strip to open the group; its tooltip shows the exact count.
Count changes animate by splitting and merging the marks. Three to two divides
the middle notch between its neighbours; two to three reverses the motion.
The morph follows `stack.animationMs`, including zero to disable animation.

The managed config retains a rolling seven days of notification events and loads
all retained notifications into history and search, without a fixed count cap.
`history.maxAgeDays: 7` sets expiry; `maxEvents: 0` and `drawerLimit: 0` remove the
event-count and drawer limits. Old events expire on startup, config changes, new
events and once a minute while idle. Recording remains disabled for transient
notifications unless `history.logTransient` is enabled.

Applications continue to send ordinary Freedesktop notifications with
`notify-send`; Notjik owns the standard desktop notification bus name.

Services can upsert a persistent card without keeping a generated ID:

```sh
notjikctl send 'Backup upload' --app backup --id nightly \
  --type progress --data '{"value":10}'
notjikctl send 'Backup upload' --app backup --id nightly \
  --type progress --data '{"value":67,"label":"Uploading archives"}'
notjikctl send 'Backup complete' --app backup --id nightly --timeout 5s
```

The same application and ID update one card in place; different applications have
separate ID namespaces. Named cards default to until-dismissed. These are live
cards, not jobs restored automatically after a daemon restart; a service can
publish the same ID again after reconnecting. The sender's title is the card
heading. Application identity remains available for grouping and logs.

SaanSeoi's scheduled daily update and monthly tiles refresh use separate persistent
results-table cards. Each run updates its card from Running to Complete, Failed, or
Unverified. Missing or malformed job summaries remain Unverified even when the
command exits successfully. Cards include publication details and reported errors,
with Open run log (when a transcript is available) and Open journal actions in
Kitty. Notification delivery failures are recorded in the service journal and do
not prevent the scheduled job from running. The scheduler implementation lives in
`saanseoi/apps/harbour-cli/src/lib/commands/schedule.ts`; the installed timers run
that source directly.

The built-in [`results-table` card](https://github.com/tijptjik/tooltjik/blob/main/apps/notjik/docs/cards.md#results-tables)
is supplied by the Notjik package; no custom component registration is needed.
Both scheduled jobs send this layout. Daily updates list published source releases
as secondary rows beneath the publication total. Tiles refreshes list each region
with its version, basemap previews, style previews and routing companion beneath it.
Errors and missing evidence are represented as explicit result rows.

## Telegram media bridge

Bridge notifications preserve Telegram's bold, italic, underline, strikethrough,
monospace/code and underlined links in messages and captions, including text
around custom emoji. Links are visual; use Open to follow them in Telegram.
Literal Markdown and HTML stay literal. Text spoilers show a placeholder directing
you to Telegram. Native Desktop notifications cannot recover formatting entities
that Telegram omits from its notification payload.

Telegram cards show the chat’s small profile photo, downloaded through TDLib,
and update when the photo changes. Initials are the fallback while loading or
when no photo is available.

Telegram cards also show WebP stickers, TGS/WebM animated stickers, GIF/MP4
animations, standalone animated emoji and inline custom emoji. Animations loop
silently while visible and stop when hidden, locked or paused. Hidden previews,
protected media and spoilers stay hidden. Run `notjikctl telegram setup` after
upgrading to install the optional Lottie renderer; FFmpeg is required. Private
rendered derivatives use seven-day retention and a 256 MiB cache target, preserving
active sources. The bridge's download limit remains 20 MiB.

Demo types include `telegram-sticker`, `telegram-animated-sticker`, `telegram-gif`,
`telegram-animated-emoji` and `telegram-custom-emoji`; they also participate in
`demo next` and `demo all`.

Notjik can show Telegram photo previews and play voice recordings with pause,
seeking and playback speed controls. The voice Play button stays visible when idle, with a dark play/pause icon.
Voice cards show Telegram’s supplied waveform
with played peaks highlighted; it is available before audio download completes.
Messages without usable waveform data retain a plain seek bar. The optional TDLib bridge uses a separate
Telegram login and supplies attachments that Telegram Desktop's native
notification payload does not include. Its source, setup script, user service,
and tests live in `tooltjik/apps/notjik`.

After installing the updated Notjik build:

```sh
notjikctl telegram setup
notjikctl telegram login
systemctl --user daemon-reload
systemctl --user enable --now notjik-telegram.service
notjikctl telegram status
```

The terminal login asks for an API ID/hash from <https://my.telegram.org/apps>,
phone number, login code and any two-step verification password. Account/session
data stays private under `~/.local/state/notjik/telegram`; never add it to Chezmoi.
The optional runtime is isolated in `~/.local/share/notjik/telegram-venv`.
The installer does not enable the bridge automatically. If signing in again,
stop the bridge first; its TDLib database has a single-writer lock.

Keep Telegram Desktop notifications enabled. Notjik suppresses its native chat
notifications only while the connected bridge renews a short lease; they resume
on bridge failure/disconnection or within 12 seconds of a missed heartbeat.
The bridge follows Telegram notification settings, leaves old unread messages
alone on startup, and does not mark messages read merely by displaying or playing
them. Its Reply and Mark read controls are explicit. Open uses a supported message
or user link when available, otherwise it opens Telegram with a status explanation.

Telegram action buttons use 20 px icons in 30 px buttons, with accessible names and no tooltips.
The action order is Mark read, Voice, Reply; Open stays on the right.

**Record** captures a voice reply from the default microphone. Use **Send** to finish capture and send, or **Reset** to cancel and discard it.
Recording alone never sends a message. One draft is supported at a time, with a five-minute limit; `ffmpeg`
and `ffprobe` with PulseAudio input and Opus support are required. Recording stops
incoming playback. Locking or pausing stops capture and keeps the draft for review.
The draft survives detachment and window moves; closing the card or exiting
Notjik deletes it. Cards holding a draft do not expire. Detached windows fit the
card height as controls open and close.

Drafts use private files under `$XDG_RUNTIME_DIR/notjik-voice`. Sending first
copies the draft into the bridge's private `voice-outbox`, keeping it until TDLib
confirms upload completion, including across bridge restarts. “Voice reply queued”
means accepted; “Voice reply sent” requires Telegram's send-success update. Failed
sends retain the draft. If confirmation times out, check Telegram before trying
again; the UI disables retry to avoid duplicates. Pending upload copies are
limited to 20. When installing bridge updates, restart `notjik-telegram.service`
as well as `notjik.service` after current notifications and drafts are cleared.

**Transcribe** on a voice card requests Telegram’s own speech recognition after
checking message eligibility. Partial and final text appear below the waveform as Telegram sends them,
without reloading the voice message or interrupting playback.
Telegram account allowances apply; unavailable transcription and service errors
are shown inline. Clicking does not mark the message read. Hidden previews remain
text-only. In demos, Transcribe displays synthetic text without contacting Telegram.

Media never autoplays; playback stops on desktop lock or dismissal.
Detached cards keep voice playback and unsent reply drafts through a move. They
hide while locked or notifications are paused; playback needs an explicit Play
after unlocking. Hidden
previews, protected/self-destructing media and spoilers remain text-only. Each
download is limited to 20 MiB. TDLib manages its cache with seven-day retention
and a 256 MiB target. The existing Notjik history policy still applies to captions
and local paths. The bridge sender is `Telegram via Notjik`; the existing blacklist
for native Telegram buttons remains unchanged. Add that bridge name to the
blacklist to disable its controls too.

`notjikctl telegram doctor` checks the runtime; `journalctl --user -u
notjik-telegram.service` shows service errors. Stop/disable that service to return
to native notifications. Synthetic acceptance tests cover the UI and transport;
real account sign-in and incoming-media delivery must be verified separately.
Voice reply tests use generated silence and a fake socket, never the microphone
or a real chat; microphone capture and delivery need a separate user-driven check.

Telegram action order is Mark read, Record, Quote reply, Reply, then Open.
Quote reply targets the selected message without an extra composer heading; Reply sends a normal chat message. Both preserve Telegram Desktop drafts.

Starting Record closes the text editor while retaining its unsent draft. A successful
text send dismisses the notification; failures keep it open with the draft intact.
Demo text sends dismiss the card without contacting Telegram.

Sender images and Telegram avatars fill an 80 px strip along the left edge, cropped to the full
card height and clipped to its rounded corners. The strip grows with expanded
controls; missing avatars keep the initials fallback.

## Structured Telegram notifications

The managed `handlers` registry currently formats StarProwlarr's four-line
`Grabbed by Sonarr/Radarr` template as a key-value card: release heading,
resolution, source, codec, event, application and indexer. It matches both
Telegram Desktop and the TDLib bridge by Telegram caller and exact chat title.
Other message formats keep their original text; no delivery or duplicate policy
changes. The original body and Telegram controls remain available.

Add rules to `home/dot_config/notjik/config.json.tmpl`. Each rule specifies `id`,
`match`, a full-body `pattern`, numbered `captures`, a target `card`, and labeled
`fields`. Tooltjik's `apps/notjik/examples/handlers.json` is the starting example;
its README documents the registry and custom QML renderers. Shared rendering
code stays in Tooltjik; personal source registrations stay in Chezmoi. Install a
Tooltjik build with handler support before applying this configuration.
