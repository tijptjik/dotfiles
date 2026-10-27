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
Chezmoi, then reload Hyprland. A Zen restart is required for stylesheet changes.
To undo, remove the import, restore the Zen `border_size = 0` rule and restart
Zen/reload Hyprland.
