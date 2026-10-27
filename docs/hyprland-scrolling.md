# Hyprland scrolling layout

Native scrolling is the default layout (Hyprland 0.56.2, Lua configuration).
Windows occupy columns on an expanding horizontal strip. This is independent of
mouse/touchpad scrolling inside applications.

Kitty uses `remember_window_size no` so it does not restore a cached maximized
state over the tiling layout. Explicit fullscreen/maximize actions still work.

## Configuration choices

Edit `home/dot_config/hypr/layouts.lua.tmpl`:

| Option | Current setting | Alternatives |
| --- | --- | --- |
| `direction` | `right` | `left`, `up`, `down` |
| `column_width` | `0.5` of available width | `0.1` through `1.0` |
| `explicit_column_widths` | `0.333, 0.5, 0.667, 1.0` | Width presets cycled by bindings |
| `fullscreen_on_one_column` | `true` | `false` keeps a lone column at its configured width |
| `focus_fit_method` | `0` (center the focused column) | `1` fits with minimal movement |
| `follow_focus` | `true` | `false` disables automatic viewport following |
| `follow_min_visible` | `0.4` | Fraction required for soft focus following; explicit focus still follows |
| `wrap_focus`, `wrap_swapcol` | `false` | Enable wrapping for layout-specific focus/swapcol commands |

Horizontal focus prefers scrolling layout focus when another column exists,
then ordinary focus at the strip ends so it can move between monitors. The wrap options concern `hl.dsp.layout("focus l/r")` and `swapcol`,
not those ordinary bindings. Workspace rules can override `layout`, with
`layout_opts = { direction = "down" }` for a different scrolling direction.
Window rules can set `scrolling_width` for app-specific initial widths.

## App defaults

Initial widths are set in `home/dot_config/hypr/windows.lua.tmpl`. On `fi`,
primary is `DP-1` and secondary is `DP-2`:

| App | Primary | Secondary |
| --- | --- | --- |
| Zed (stable, Preview, Nightly) | 100% | 100% |
| Spotify | 100% | 100%; opens on workspace 20, the secondary display's tenth workspace |
| Zen | 50% | 100% |
| Kitty | 50% | 75% |
| Files / Nautilus | 50% | 75% |
| Sublime Text | 50% | 100% |
| Obsidian | 50% | 100% |
| Codex LB (both launcher entries) | 50% | 100% |
| System Monitor | 50% | 75% |

ZapZap, ChatGPT, and Signal keep their existing floating layouts on `fi`.
The current Codex LB launcher is routed to workspace 15 and explicitly gets its
secondary-display width even when launched from the primary display.

On `li`, Zed and Spotify use 100%, the other listed apps use 50%, and Spotify opens
on workspace 10. Other apps retain the 50% global default. Existing floating
rules are unaffected. `scrolling_width` sets an initial column width, not
fullscreen mode; a lone column still fills the workspace because
`fullscreen_on_one_column` is enabled. Moving an existing window between displays
does not reapply these initial-width rules. Width matching happens before later
launch overrides or session-restoration helpers transfer a window to another
workspace; such transfers retain the width chosen on the initial workspace.

The secondary overrides use `match.workspace = "m[DP-2]"`, after the base app
rules. Workspace IDs 1-10 remain on the primary display, and 11-20 on secondary.
Apply window defaults with `chezmoi apply --include=files ~/.config/hypr/windows.lua`,
then `hyprctl reload config-only` and `hyprctl configerrors`.

## Focus-sensitive gaps

`scrolling_gaps.lua` keeps windows tiled, with compositor and client fullscreen
states unchanged. When the focused scrolling column has width 1.0 and contains
one window, a temporary workspace rule removes inner/outer gaps, borders, and
rounding. Focusing a narrower tiled column in the same workspace disables that
override and restores the existing rules. Each workspace remembers its own mode;
scratch/special workspaces, floating overlays, temporary loss of window focus,
and focus on other workspaces or displays do not change the underlying strip.
Half-width columns temporarily expanded because they are alone are excluded.

The override uses a separate workspace selector and never replaces monitor or
placement rules. Consecutive 100% columns on the same workspace reuse it without
an intermediate gap transition. Geometry uses ordinary window animations; there
is no fullscreen transition or layer visibility change. Super+Left/Right prefer
native scrolling focus within the strip and ordinary focus at its ends.

## Controls

| Shortcut | Action |
| --- | --- |
| Super+F6 / Super+F7 | Switch default layout to scrolling / master |
| Super+Left / Right | Focus window; viewport follows |
| Super+Alt+arrows / Super+Shift+arrows | Resize windows (128px steps) |
| Super+Ctrl+arrows | Existing move controls |
| Super+[ / ] | Previous / next column width preset |
| Super+Page Up / Page Down | Move viewport one column backward / forward |
| Super+Alt+mouse wheel | Move viewport one column |
| Super+Home | Fit active column |
| Super+End | Fit all columns |
| Super+Ctrl+[ | Consume window into previous column |
| Super+Ctrl+] | Expel window into its own column |
| Three-finger horizontal swipe | Scroll viewport on a touchpad |

Super+mouse wheel still switches workspaces. Master-specific Super+Delete bindings
remain available when using master. Layout switching affects workspaces using the
default layout and lasts until reload; the persisted default is scrolling.

To try it, open at least three tiled windows on one workspace, then focus left/right,
cycle widths, and compare master with scrolling. One column fills the screen by design.

## Apply and revert

Apply only these files:

```sh
chezmoi apply ~/.config/hypr/variables.lua ~/.config/hypr/layouts.lua ~/.config/hypr/bindings.lua
hyprctl reload config-only
hyprctl configerrors
```

For a persistent return to master, change `general.layout` in
`home/dot_config/hypr/variables.lua` to `"master"` and apply that file.

Reference: <https://wiki.hypr.land/Configuring/Layouts/Scrolling-Layout/>
Gesture reference: <https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/>
