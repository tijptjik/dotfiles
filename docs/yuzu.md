# Yuzu

Following the installation of yuzu from flatpak, you can install the firmware and prod.keys using the following:

1. Install [Yuzu Firmware](https://prodkeys.net/yuzu-firmware-v3/) into `$HOME/.var/app/org.yuzu_emu.yuzu/data/yuzu/nand/system/Contents/registered`
2. Check if there are new [prod.keys](https://prodkeys.net/yuzu-prod-keys-n25/) releases and if so, copy them into `$HOME/.var/app/org.yuzu_emu.yuzu/data/yuzu/keys`. This is managed by chezmoi externals.
