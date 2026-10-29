# Kitty terminal icon

Kitty uses Neuwaita's charcoal terminal icon with a cyan prompt, matching the
desktop's Neuwaita theme and Rose Punk colours. The SVG is copied unchanged from
[`org.gnome.Console.svg`](https://github.com/RusticBard/Neuwaita/blob/main/scalable/apps/org.gnome.Console.svg).
Upstream supplies it under [CC0](licenses/neuwaita-CC0.txt).

Tjikup manages these user-wide overrides:

- `~/.config/kitty/kitty.app.png`: Kitty's native custom window icon and default
  notification image (Notjik displays robot portraits for Kitty reports instead).
  Kitty reads this at startup; restart existing Kitty
  processes to pick it up reliably.
- `~/.local/share/icons/hicolor/scalable/apps/kitty.svg`: scalable launcher icon.
- `~/.local/share/icons/hicolor/256x256/apps/kitty.png`: PNG alias of the custom icon.
- `~/.local/share/icons/Neuwaita/scalable/apps/kitty.svg`: alias to the managed SVG,
  overriding Neuwaita's cat icon before theme fallback occurs.

Apply only these paths when other configuration work is pending:

```sh
dotjik apply
  ~/.local/share/icons/hicolor/scalable/apps/kitty.svg \
  ~/.local/share/icons/hicolor/256x256/apps/kitty.png \
  ~/.local/share/icons/Neuwaita/scalable/apps/kitty.svg
```

After replacing or updating Neuwaita, reapply the managed override. Other themes
with their own Kitty icon can take precedence over the hicolor fallback.
Existing notification history may retain the old image.
On the current desktop, Neuwaita has no icon cache; GTK's cache generator rejects
the theme with `The generated cache was invalid`. The installed icon files are
verified directly. Restart a launcher if it retains an image in memory.

Regenerate the committed 256-pixel PNG from the SVG with ImageMagick:

```sh
magick -background none native/home/files/.local/share/icons/hicolor/scalable/apps/kitty.svg \
  -resize 256x256 native/home/files/.config/kitty/kitty.app.png
```
