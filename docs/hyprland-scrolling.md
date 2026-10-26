# Hyprland scrolling layout

Native scrolling is the default layout (Hyprland 0.56.2, Lua configuration).
Windows occupy columns on an expanding horizontal strip. This is independent of
mouse/touchpad scrolling inside applications.

## Configuration choices

Edit `home/dot_config/hypr/layouts.lua.tmpl`:

| Option | Current setting | Alternatives |
| --- | --- | --- |
| `direction` | `right` | `left`, `up`, `down` |
| `column_width` | `0.5` of available width | `0.1` through `1.0` |
| `explicit_column_widths` | `0.333, 0.5, 0.667, 1.0` | Width presets cycled by bindings |
| `fullscreen_on_one_column` | `true` | `false` keeps a lone column at its configured width |
| `focus_fit_method` | `1` (fit with minimal movement) | `0` centers the focused column |
| `follow_focus` | `true` | `false` disables automatic viewport following |
| `follow_min_visible` | `0.4` | Fraction required for soft focus following; explicit focus still follows |
| `wrap_focus`, `wrap_swapcol` | `false` | Enable wrapping for layout-specific focus/swapcol commands |

Existing directional focus bindings use ordinary focus, so they can move between
monitors. The wrap options concern `hl.dsp.layout("focus l/r")` and `swapcol`,
not those ordinary bindings. Workspace rules can override `layout`, with
`layout_opts = { direction = "down" }` for a different scrolling direction.
Window rules can set `scrolling_width` for app-specific initial widths.

## Controls

| Shortcut | Action |
| --- | --- |
| Super+F6 / Super+F7 | Switch default layout to scrolling / master |
| Super+Left / Right | Focus window; viewport follows |
| Super+Shift+arrows | Existing resize controls |
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
