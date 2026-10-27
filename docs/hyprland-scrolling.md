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
| `explicit_column_widths` | `0.333, 0.5, 0.667, 1.0` | Native cycling presets; our arrow bindings use absolute widths |
| `fullscreen_on_one_column` | `false` | A lone column keeps its configured width |
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

App widths are set in `home/dot_config/hypr/windows.lua.tmpl`. On `fi`,
primary is `DP-1` and secondary is `DP-2`:

| App | Primary | Secondary |
| --- | --- | --- |
| Zed (stable, Preview, Nightly) | 100% | 100% |
| Spotify | 100% | 100%; opens on workspace 20, the secondary display's tenth workspace |
| Zen | 50% | 100% |
| Kitty | 50% | 75% |
| Files / Strata / Nautilus | 50% | 75% |
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
fullscreen mode. A lone column keeps its configured width because
`fullscreen_on_one_column` is disabled.

`scrolling_widths.lua` reapplies registered widths when a tiled window arrives on
a different monitor, including workspace transfers. It reuses the app matches
and widths registered through `widths.rule` in `windows.lua`; routing-only launch
overrides remain ordinary `hl.window_rule` calls. Destination output matching is
read directly because native workspace tags can lag behind a move. A one-shot
1ms event-loop callback lets the compositor finish attaching the destination
column before resizing it. Same-monitor moves preserve manual widths; floating,
fullscreen, scratch windows and apps without registered widths are ignored.
Scratch visits retain the last ordinary monitor. Resizing a stacked window changes
its shared column width. The gap policy is refreshed after the resize.
For silent transfers, the native fractional resize needs temporary column focus;
the handler restores the original visible workspace, focus and pointer in the
same event-loop turn. Clients can still receive the intermediate focus events.

The secondary overrides use `match.workspace = "m[DP-2]"`, after the base app
rules. Workspace IDs 1-10 remain on the primary display, and 11-20 on secondary.
Apply window defaults with `chezmoi apply --include=files ~/.config/hypr/windows.lua ~/.config/hypr/scrolling_widths.lua ~/.config/hypr/hyprland.lua`,
then `hyprctl reload config-only` and `hyprctl configerrors`.

## Gap transitions

The `scrolling-gaps` C++ plugin keeps workspace gaps and logical column footprints
constant. Each workspace's last-focused, single-window 100% scrolling column gets
an expanded visual rectangle with no border or rounding. Moving focus to another
monitor or workspace preserves that geometry. Focusing another column within the
same workspace restores its ordinary gapped rectangle through `windowsMove`. Narrower and stacked columns retain their
normal content dimensions throughout navigation. Neither client nor compositor
fullscreen is used. Special workspaces preserve the underlying normal workspace's
last-focused column, including during transient loss of focus and plugin reload.
Panel reservations, layer visibility, and floating windows
retain normal behavior. Explicit user fullscreen is left to Hyprland.

The plugin hooks the native window-target geometry, border/rounding accessors,
and window hit testing. Within expanded full-width content, covered neighboring
columns must not capture edge clicks through their original logical footprints.
Hit testing rechecks the visible geometry while retaining native floating-window,
popup, modal, and special-workspace priority. Focus-follows-mouse settings are unchanged.
It checks the compositor ABI before installing hooks and fails closed on mismatch.
A missing plugin leaves ordinary gaps everywhere; there is no workspace-wide or
fullscreen fallback. `scrolling_gaps.lua` only dispatches navigation and widths.

Source and build helper live in
`home/dot_local/share/hypr/plugins/scrolling-gaps/`. With development headers for
the installed compositor (`hyprland-devel` and its dependencies):

```sh
~/.local/share/hypr/plugins/scrolling-gaps/build.sh
hyprctl reload config-only
hyprctl configerrors
```

The build helper also accepts `SCROLLING_GAPS_SDK_DIR`, an extracted development-RPM
root containing `usr/include`, and an optional output `.so` path. It replaces the
binary atomically. `plugins.lua` loads `~/.local/lib/hypr/scrolling-gaps-local.so` when
present. Rebuild after a compositor ABI change. To replace an already loaded
build, unload it before reloading configuration:

```sh
hyprctl plugin unload ~/.local/lib/hypr/scrolling-gaps-local.so
hyprctl plugin load ~/.local/lib/hypr/scrolling-gaps-local.so
hyprctl reload config-only
```

For rollback, move the binary aside and reload configuration. Ordinary gapped
geometry is restored; shortcuts continue to work. `hyprctl scrolling-gaps:state`
reports current rendered sizes, goal sizes, and which window is gapless, without
window titles or application content.
`hyprctl scrolling-gaps:hit-test X Y` reports the window address targeted at a
global logical coordinate without moving the pointer or sending a click.

Validation used an isolated compositor, a reserved top panel, and three synthetic
terminals. Across 96 animation samples, ordinary windows retained identical current
and goal sizes while the wide window animated; all fullscreen states stayed zero.
The packaged probe is `scripts/check-scrolling-gaps.py --instance SIGNATURE
--plugin /path/to/scrolling-gaps-local.so --artifacts /tmp/gap-check`. It requires an
empty disposable compositor, refuses the current desktop instance, and closes
the disposable compositor after testing. It also checks floating-window visibility
and excludes stacked columns. Two synthetic monitors additionally check that
cross-monitor focus and plugin reload preserve both gapless columns. It requires
Kitty, Waybar, and grim.
The probe also checks 108 edge/interior targets across left, middle and right
full-width columns with border resizing enabled, plus floating-window hit priority.

The remaining app redraw behavior belongs only to the deliberately resizing 100%
window, not the ordinary column coming into view.

## Controls

| Shortcut | Action |
| --- | --- |
| Super+F6 / Super+F7 | Switch default layout to scrolling / master |
| Super+Left / Right | Focus previous / next column; cross monitors at strip edges |
| Super+Up / Down | Focus within the current column (native focus wrapping) |
| Super+Shift+Left / Right | Move the whole column left / right; cross monitors and wrap at strip edges |
| Super+Shift+Up / Down | Reorder the active window within its column, wrapping at either end |
| Super+Ctrl+Left / Right | Transfer the active window into an existing adjacent column |
| Super+Ctrl+Shift+Left / Right | Extract the active window into its own column on that side |
| Super+Alt+Up / Right / Down / Left | Set column width to 100% / 75% / 50% / 25% |
| Super+Page Up / Page Down | Move viewport one column backward / forward |
| Super+Alt+mouse wheel | Move viewport one column |
| Super+Home | Fit active column |
| Super+End | Fit all columns |
| Three-finger horizontal swipe | Scroll viewport on a touchpad |

At a horizontal strip edge, Super+Shift+Left/Right sends the whole column to
the adjacent monitor's active ordinary workspace. Monitors are ordered by screen
position, left to right (then top to bottom), excluding mirrors and powered-off
outputs. Right enters the destination's first column position; left enters its
last. Moving right off the rightmost monitor wraps to the leftmost monitor, and
left wraps in reverse. With one monitor, the column wraps within its workspace.
Stacked windows retain their top-to-bottom order and focus follows the original
active window. Destination app widths are reapplied. Scratch workspaces,
fullscreen windows and destinations using a different layout are excluded.

A group here means a scrolling column, not a Hyprland tabbed window group.
Transfers use native insertion at the pointer's vertical position and retain focus
on the moved window. A missing adjacent column makes transfer a no-op. Extraction
from a singleton column is a no-op. Vertical reordering preserves the relative
order of the other windows, including when wrapping. These operations are scoped
to tiled scrolling windows. The old bracket bindings and Ctrl+Up/Down are removed;
Shift+arrows no longer resize. Width shortcuts also apply to lone columns and refresh gaps
immediately: 100% removes gaps/borders/rounding for a single-window column;
75%, 50%, and 25% restore them. Stacked columns retain ordinary gaps at 100%.

Super+mouse wheel still switches workspaces. Master-specific Super+Delete bindings
remain available when using master. Layout switching affects workspaces using the
default layout and lasts until reload; the persisted default is scrolling.

To try it, open at least three tiled windows on one workspace, then focus left/right,
set widths, and compare master with scrolling. A lone column should retain its configured width.

## Apply and revert

Apply only these files:

```sh
chezmoi apply ~/.config/hypr/variables.lua ~/.config/hypr/layouts.lua ~/.config/hypr/bindings.lua ~/.config/hypr/scrolling_shortcuts.lua ~/.config/hypr/scrolling_gaps.lua ~/.config/hypr/plugins.lua
hyprctl reload config-only
hyprctl configerrors
```

For a persistent return to master, change `general.layout` in
`home/dot_config/hypr/variables.lua` to `"master"` and apply that file.

Reference: <https://wiki.hypr.land/Configuring/Layouts/Scrolling-Layout/>
Gesture reference: <https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/>
