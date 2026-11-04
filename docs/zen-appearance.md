# Zen window appearance

Zen uses the shared Hyprland frame, like Kitty. Its window rule deliberately
does not override `border_size`; colours, thickness and outer rounding come
from `hypr/variables.lua` and `hypr/colors.lua`.

`~/.config/zen/userChrome.css` removes Zen's own perimeter spacing and gives
each webview an 8px clipped inner radius. Browser/DOM fullscreen and Glance
overlays retain Zen's native handling. The compact sidebar uses Kitty's solid
Rosé Punk background (`#191724`) with 8px corners, no grain, gradient, border,
outline or shadow. Its controls and hover behaviour retain Zen's styling.
This stylesheet targets the installed Zen selectors;
check compact-mode hover, split views and fullscreen after browser updates.

Sidebar opening and the Transparent Zen content-push animation use a bounded
ease-out curve instead of Zen's overshooting spring. Content corners on the
sidebar side are square when it is docked or explicitly pinned (`zen-user-show`),
including compact mode that hides only the toolbar. Temporary hover reveals
retain the rounded content corners. Both left and right sidebar positions are
handled; the opposite side keeps its 8px corners.

Split panes retain a 4px divider in both directions, independently of the zero
perimeter spacing. The gap background matches Hyprland's active `#1f1d2e` and
inactive `#26233aaa` border values; Zen's selected-pane outline is suppressed
so it cannot cover the divider. The divider remains draggable. Keep the
`--tijp-split-border-*` CSS values aligned with Hyprland if its border theme or
width changes. Inactive alpha is composited over Zen's background, so its final
appearance can differ from Hyprland's border over the desktop.

The stylesheet must be loaded by each desired Zen profile. In `about:profiles`,
open that profile's root directory and create `chrome/userChrome.css` containing
the following import (before any other CSS rules):

```css
@import url("../../../.config/zen/userChrome.css");
```

This relative path assumes profiles live directly under `~/.zen/`. Preserve any
existing profile CSS. Enable
`toolkit.legacyUserProfileCustomizations.stylesheets` in `about:config` and
restart Zen. Do not edit the generated `zen-themes.css` or the running browser's
`prefs.js`. Profile registration is local; Zen sync is not assumed to sync CSS.

Apply just `~/.config/zen/userChrome.css` and `~/.config/hypr/windows.lua` with
Tjikup, then reload Hyprland. A Zen restart is required for stylesheet changes.
To undo, remove the import, restore the Zen `border_size = 0` rule and restart
Zen/reload Hyprland.

## Compact-mode edge hover

The Fi, Li and Si system autoconfig files set
`zen.view.compact.hover-hack-delay` to 300 ms, requiring a sustained edge hover
before the compact sidebar or toolbar opens. Zen also uses this delay for
hover-leave checks. This uses Zen's native timer and cancellation handling.

Apply the host's native system manifest with the `zen` group, then restart Zen
when convenient. The preference is set at startup for every profile and is not
locked. No profile CSS change is needed.

## Closing the last regular tab

Dotjik manages `~/.config/zen/close-last-regular-tab.sys.mjs` in the `zen`
home-file group. `home:config:zen` follows `home:files` for all roles. Fi, Li and
Si system manifests manage `/opt/zen/config.js` and
`/opt/zen/defaults/pref/config-prefs.js` (Si targets the resolved
`/mnt/storage/meta/opt/zen/` directory because `/opt` is a symlink); this loads the behavior for every profile,
including profiles created later. Existing per-profile userChromeJS loaders are
preserved. The installed RPM does not own either autoconfig file.

Only a completed `TabClose` carrying Zen's explicit
`metricsContext.isUserTriggered` marker can trigger window closure. Keyboard,
close-button and context-menu handlers carry that marker; startup cleanup and
window-sync removals do not. The active window closes only if no regular tabs
remain, including other workspaces and collapsed groups. Pinned tabs, Essentials,
Glance overlays and internal empty tabs are excluded. The normal window-close
command retains unload prompts. An empty or pinned-only startup stays open.

Apply the home file with `tjikup workflow files home-files apply --group zen`.
Apply the system loader through the native system manifest's `zen` group (normal
system-file applies also include it). No browser restart is forced: restart Zen
when convenient to activate changes. The managed script's window marker prevents
duplicate listeners when an older per-profile copy is present.

This depends on Zen's chrome APIs; retest empty startup, explicit last-tab
closure, pins/Essentials and multiple synced windows after browser updates.
To disable immediately, rename the managed `.sys.mjs` file and restart Zen;
remove its manifest entries as well to prevent a later apply from restoring it.
