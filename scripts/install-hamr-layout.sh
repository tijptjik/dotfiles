#!/usr/bin/env bash
# Build the small local GTK layout patch against a verified release commit.
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
revision=3a49c02a0aee39185686b33e6d0b645cb3d632c9
patch_file="$repo_dir/scripts/hamr/center-modes.patch"
install_dir="$HOME/.local/share/hamr-layout"
build_dir="${XDG_CACHE_HOME:-$HOME/.cache}/hamr-layout/$revision"
fingerprint=$(sha256sum "$patch_file" | cut -d ' ' -f 1)
receipt="$revision:$fingerprint"

if [[ -x "$install_dir/hamr-gtk" && -f "$install_dir/receipt" ]] &&
   [[ $(cat "$install_dir/receipt") == "$receipt" ]]; then
    exit 0
fi

pkg-config --exists gtk4 gtk4-layer-shell-0 || {
    echo 'Hamr layout build requires gtk4-devel and gtk4-layer-shell-devel.' >&2
    exit 1
}
mkdir -p "$build_dir" "$install_dir"
exec 9>"$build_dir/build.lock"
flock 9
source_dir="$build_dir/source-$fingerprint"
if [[ ! -f "$source_dir/.layout-patched" ]]; then
    staging=$(mktemp -d "$build_dir/source.XXXXXX")
    trap 'rm -rf -- "$staging"' EXIT
    git -C "$staging" init --quiet
    git -C "$staging" fetch --depth 1 https://github.com/Stewart86/hamr.git "$revision"
    git -C "$staging" checkout --quiet --detach FETCH_HEAD
    [[ $(git -C "$staging" rev-parse HEAD) == "$revision" ]]
    git -C "$staging" apply --check "$patch_file"
    git -C "$staging" apply "$patch_file"
    touch "$staging/.layout-patched"
    mv -- "$staging" "$source_dir"
    trap - EXIT
fi
(
    cd -- "$source_dir"
    export CARGO_TARGET_DIR="$build_dir/target"
    cargo build --locked --release -p hamr-gtk -j "${HAMR_BUILD_JOBS:-2}"
    cargo test --locked --release -p hamr-gtk horizontal_anchor_tests -j "${HAMR_BUILD_JOBS:-2}"
)
install -m 755 "$build_dir/target/release/hamr-gtk" "$install_dir/hamr-gtk.new"
mv -f -- "$install_dir/hamr-gtk.new" "$install_dir/hamr-gtk"
printf '%s\n' "$receipt" > "$install_dir/receipt"
systemctl --user daemon-reload
if systemctl --user is-active --quiet hamr-gtk.service; then
    systemctl --user restart hamr-gtk.service
fi
