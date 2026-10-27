# Chat workspace appearance

ZapZap (`com.rtosta.zapzap`) and Signal (`org.signal.Signal`) use the theme panel background and off-white
while unfocused in `special:chat`, with a subtle 1.2px Gaussian blur and
20% brightness reduction. Focus restores their original colours and sharpness.
Telegram is excluded from all four shader rules and bypasses the plugin rendering path entirely.
The local renderer patch only admits ZapZap and Signal in `special:chat`; all other
surfaces go directly to Hyprland’s original renderer. Inputs are normalized to sRGB
using the native renderer before applying the shared palette.
The monochrome effect does not affect other applications or workspaces.

`hypr/chat_appearance.lua` loads `~/.local/lib/hypr/HyprWindowShade.so` when
present and adds workspace-scoped inactive/focus/unfocus shader tags.
Focus changes use a 200ms smoothstep fade; replace-mode ensures that each
transition samples the original colour texture rather than stacking effects. The GLSL shader
treats the matched chat windows as opaque (RGBX buffers need not provide
meaningful alpha) and computes luminance with Rec. 709 weights. Each sample uses a smooth transition from 0.20 to 0.50, followed by a
1.2-logical-pixel 3x3 Gaussian coverage filter. Filtering after the threshold preserves
thin text better than blurring its luminance before thresholding.
The palette matches the Rosé Punk panel: `#1f1d2e` and `#e5e5e5`,
multiplied by 0.8 while unfocused. Sampling offsets use the plugin
`surface_size` uniform, not an imported buffer texture-size query.

The native `decoration.dim_special = 0.65` adds a 65% pure-black scrim
behind all special workspaces. Their foreground windows remain undimmed.
The rule deliberately uses a bare tag: in Hyprland 0.56.2, a `+` prefix is
stripped when applying a dynamic tag but not when removing it, leaving it
attached after the workspace changes.

## Plugin build

Upstream: https://github.com/ManofJELLO/HyprWindowShade

The build helper pins upstream commit
`a4c6b8af424a189072427c4c90ef2938e1b481d3`, its release for Hyprland 0.56.2
(`efb50993780079460b0cbed1363e2166a2de1d9f`). It adds an ABI check before
installing any hooks. It does not load the plugin or restart Hyprland.

With matching Hyprland, Lua and glslang development headers installed:

```sh
~/.local/share/hypr/plugins/windowshade/build.sh
hyprctl reload
```

For an extracted development SDK, set `HYPRWINDOWSHADE_SDK_DIR` to the
root containing `usr/include/hyprland` and use `CPPFLAGS=-I/path/to/include`
for any separately extracted Lua/glslang headers. No system package changes
are required. Sources are fetched into `~/.cache/hypr-windowshade`; the
binary is atomically installed under `~/.local/lib/hypr`.

After a Hyprland upgrade, review upstream compatibility and its release pin
before rebuilding. A binary with a different internal ABI refuses to load.

## Verification

Headless checks passed for intermediate fade frames, both focus directions,
matching tint for identical Signal/ZapZap inputs, and removal outside chat.
The synthetic Telegram window had zero pixel difference with the plugin loaded
versus unloaded.

After installation, live captures with focus/workspace assertions confirmed both
Signal and ZapZap stay within the subdued palette, retain visible content, and
restore colour on focus. Telegram's actual instance-suffixed class takes the
hard bypass. In its live loaded/unloaded comparison, 247 of 249 previously stable
64px tiles were pixel-identical; changing content prevents whole-window equality.
This is supported by the exact synthetic Telegram comparison, not tags alone.
Focus, workspace visibility and mouse-follow settings were restored. No chat
applications were restarted.

To disable, remove/comment `require("chat_appearance")` in `hypr/plugins.lua`,
reload, then unload the plugin with
`hyprctl plugin unload ~/.local/lib/hypr/HyprWindowShade.so`.
