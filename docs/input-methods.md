# Chinese input on Hyprland

Fcitx 5 starts with the Hyprland session. The common RPM list in
`../chezetc/etc/.chezmoidata/packages.yaml` installs the engines, GTK/Qt modules,
configuration tool, and Chinese fonts on all managed hosts.

The Default group contains US International with AltGr accents (`EN`), predictive Mandarin Pinyin
(`拼`), and Quick Classic / 速成 (`速`). Pinyin uses local prediction and OpenCC
Traditional Chinese conversion with Hong Kong character variants. Quick Classic
already outputs Traditional characters. Additional Cantonese / Quick 3 and UK
groups present during setup are retained.

## Preserving the live profile

`tjikup` captures `~/.config/fcitx5/profile` before committing and pulling, using
the same propagation workflow as Zed and Herdr. The current group order and
default input methods are accepted exactly as Fcitx writes them; they are not
sorted or reset to the repository's previous order.

Every normal run with a profile present saves an owner-only, timestamped copy
under `~/.local/state/tjikup/backups/fcitx/` (or `$XDG_STATE_HOME/tjikup/backups/fcitx/`).
The backup contains the captured live bytes and is saved before source updates.
Backups are retained, including on runs where the profile has not changed.
`tjikup --dry-run` does not create these backups or change the source.

This prevents the usual profile-order overwrite prompt when applying through
`tjikup`. A direct `chezmoi apply` does not capture live state first; use `tjikup`
after changing input-method preferences. Git merge conflicts between devices,
or further profile edits while the update is running, remain separate cases.

## Input indicator

The input indicator shares the clock pill. Fcitx's notificationitem add-on is
disabled to avoid a duplicate tray indicator.

- Click the input indicator to cycle the current group's methods.
- Right-click it to open Fcitx settings.
- Ctrl+Space toggles English and Chinese.
- Ctrl+Shift+Space cycles methods, including English.
- Number keys select candidates; Space selects the current Pinyin candidate.
- Ctrl+Shift+F toggles Simplified/Traditional conversion; Traditional is the
  managed default for Pinyin.

Hyprland's keyboard layout is `us` / `altgr-intl`, matching the Default group's
`keyboard-us-altgr-intl`. Apostrophes, quotes, backticks, and carets type immediately; accent dead keys
require AltGr (Right Alt). The extra UK group is retained, but Fcitx cannot change
Hyprland's physical keyboard layout when switching groups.
The recurring Wayland layout advisory is hidden through Fcitx's notifications
configuration (`wayland-diagnose-other`). Other notifications remain enabled.

GTK Wayland, Kitty, and the Chromium launchers use native Wayland text input.
Fcitx supplies input-method popup surfaces, so candidate lists stay beside the
caret and do not enter the tiling layout. No floating rule for the settings
window is needed to achieve this. GTK's X11 settings and Qt's Fcitx module cover
toolkit applications that do not use native Wayland text input.

Do not globally set `GTK_IM_MODULE=fcitx`: GTK Wayland should use its native
text-input protocol. `XMODIFIERS=@im=fcitx` provides X11 compatibility. Chrome,
Canary, Brave, and Electron launchers enable Wayland IME with text-input-v3.
Kitty explicitly uses its Wayland backend. Firefox/Zen use GTK's native Wayland
input path when running on Wayland.

After applying, log out and back in for a consistent session environment, or
restart affected apps. Already-running browser processes do not adopt new launch
flags merely by opening another window. Apply chezetc and chezmoi on other hosts;
installing packages on one host does not install them remotely.

Validation on Fedora 44 / Hyprland 0.56.2: native GTK 4 text editor, Wayland Chrome,
and Kitty all displayed caret-anchored candidates and committed `中國` from
Pinyin and `仁` from Quick (`om`, candidate 1). Candidate surfaces did not appear
as tiled clients. Other applications and Flatpak runtimes were not individually
tested.
