#!/usr/bin/env bash
# Tjikup policy: rebuild only the local scrolling-gap plugin after RPM updates.
set -euo pipefail
mode=${1:-apply}
[[ "$mode" == apply || "$mode" == --check ]] || { echo "Usage: $0 [--check]" >&2; exit 2; }
if ! command -v Hyprland >/dev/null; then
    echo 'Hyprland not installed; scrolling-gap plugin not needed'
    exit 0
fi
repo=${DOTJIK_REPO:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)}
source_dir="$repo/native/home/files/.local/share/hypr/plugins/scrolling-gaps"
cache="${XDG_CACHE_HOME:-$HOME/.cache}/tjikup/scrolling-gaps"
output="$HOME/.local/lib/hypr/scrolling-gaps-local.so"
receipt="$cache/build.receipt"
for tool in jq rpm sha256sum strings; do command -v "$tool" >/dev/null; done
version=$(Hyprland --version-json)
commit=$(jq -er '.commit | select(test("^[0-9a-f]{40}$"))' <<< "$version")
abi=$(jq -er '.abiHash | select(type == "string" and length > 0)' <<< "$version")
packages=()
for package in hyprland aquamarine hyprutils hyprgraphics hyprlang hyprcursor; do
    packages+=("$(rpm -q --qf '%{NAME}-devel-%{VERSION}-%{RELEASE}.%{ARCH}' "$package")")
done
fingerprint=$({ printf '%s\n' "$abi" "${packages[@]}"; sha256sum "$source_dir/main.cpp" "$source_dir/build.sh" "${BASH_SOURCE[0]}"; } | sha256sum | cut -d ' ' -f 1)
current() {
    [[ -s "$output" && -f "$receipt" ]] || return 1
    [[ $(cat "$receipt") == "$(printf '%s\n%s' "$fingerprint" "$(sha256sum "$output" | cut -d ' ' -f 1)")" ]]
}
# A read-only check covers the build; apply also reconciles session activation.
if [[ "$mode" == --check ]]; then current; exit $?; fi
mkdir -p "$cache" "$(dirname -- "$output")"
exec 9>"$cache/build.lock"
flock 9
stage=
trap '[[ -z "$stage" ]] || rm -rf -- "$stage"' EXIT
if ! current; then
    for tool in dnf rpm2cpio cpio rpmkeys pkg-config "${CXX:-c++}"; do command -v "$tool" >/dev/null; done
    stage=$(mktemp -d "$cache/build.XXXXXX")
    sdk_key=$(printf '%s\n' "${packages[@]}" | sha256sum | cut -d ' ' -f 1)
    sdk="$cache/sdk-$sdk_key"
    if [[ ! -f "$sdk/.complete" ]]; then
        mkdir -p "$stage/rpms" "$stage/sdk"
        # Download exact installed runtime counterparts, never upgrade the system.
        # Scanner headers have no runtime ABI; other build tools come from system:rpm.
        # Reuse metadata from the preceding root RPM update without refreshing
        # repositories or writing to its cache. RPMs go to our staging directory.
        dnf download --destdir "$stage/rpms" --setopt=cachedir=/var/cache/libdnf5 \
            --setopt=cacheonly=metadata --setopt=build_cache=False \
            "${packages[@]}" hyprwayland-scanner-devel
        for archive in "$stage/rpms/"*.rpm; do
            rpmkeys --checksig "$archive"
            # cpio can stop at the end marker before rpm2cpio finishes writing
            # padding, causing SIGPIPE under pipefail. Check conversion and
            # extraction separately so genuine failures still stop the build.
            rpm2cpio "$archive" > "$stage/payload.cpio"
            (cd "$stage/sdk"; cpio -idm --quiet < "$stage/payload.cpio")
            rm -- "$stage/payload.cpio"
        done
        grep -Fq "\"$commit\"" "$stage/sdk/usr/include/hyprland/src/version.h" || {
            echo 'Downloaded headers do not match installed Hyprland; leaving plugin untouched' >&2; exit 1;
        }
        touch "$stage/sdk/.complete"
        # A partial SDK from an interrupted earlier run is disposable cache.
        rm -rf -- "$sdk"
        mv "$stage/sdk" "$sdk"
    fi
    SCROLLING_GAPS_SDK_DIR="$sdk" bash "$source_dir/build.sh" "$stage/plugin.so"
    strings "$stage/plugin.so" > "$stage/strings"
    grep -Fxq "$commit" "$stage/strings" || { echo 'Plugin commit verification failed' >&2; exit 1; }
    [[ $(Hyprland --version-json | jq -er '.abiHash') == "$abi" ]] || {
        echo 'Hyprland changed during build; retry on the next Tjikup run' >&2; exit 1;
    }
    # Install on the destination filesystem atomically; keep the last binary for recovery.
    if [[ -f "$output" ]]; then cp -p "$output" "$output.previous"; fi
    install -m 755 "$stage/plugin.so" "$output.new"
    mv -f "$output.new" "$output"
    printf '%s\n%s\n' "$fingerprint" "$(sha256sum "$output" | cut -d ' ' -f 1)" > "$receipt.new"
    mv -f "$receipt.new" "$receipt"
    echo 'Rebuilt scrolling-gap plugin for installed Hyprland'
else
    echo 'Scrolling-gap plugin already matches installed Hyprland and source'
fi
# Never unload a plugin from an older compositor after an on-disk RPM upgrade.
# The normal Lua loader will use the new binary at the next login.
signature=${HYPRLAND_INSTANCE_SIGNATURE:-}
if [[ -z "$signature" ]]; then
    echo 'Plugin ready; no current Hyprland session, loads at next login'
    exit 0
fi
running=$(hyprctl -j version) || { echo 'Plugin ready; current session unavailable, loads at next login'; exit 0; }
if [[ $(jq -er '.abiHash' <<< "$running") != "$abi" ]]; then
    echo 'Plugin ready for upgraded Hyprland; log out and back in to use it (current session preserved)'
    exit 0
fi
activation="$cache/active-$(printf '%s' "$signature" | sha256sum | cut -d ' ' -f 1)"
binary_hash=$(sha256sum "$output" | cut -d ' ' -f 1)
loaded=$(hyprctl -j plugin list | jq -er 'any(.[]; .name == "scrolling-gaps")') || [[ "$loaded" == false ]]
if [[ "$loaded" == true && -f "$activation" && $(cat "$activation") == "$binary_hash" ]]; then
    echo 'Scrolling-gap plugin active in current session'
    exit 0
fi
plugin_command() {
    local response
    response=$(hyprctl plugin "$1" "$output") && [[ "$response" == ok ]]
}
if [[ "$loaded" == true ]]; then plugin_command unload; fi
if ! plugin_command load; then
    echo 'Plugin activation failed; restoring previous binary when available' >&2
    rm -f "$receipt" "$activation"
    if [[ -f "$output.previous" ]]; then
        install -m 755 "$output.previous" "$output.new"
        mv -f "$output.new" "$output"
        # Keep the native ABI guard enabled for the rollback too.
        plugin_command load || true
    fi
    exit 1
fi
hyprctl scrolling-gaps:state | jq -e 'type == "array"' >/dev/null
printf '%s\n' "$binary_hash" > "$activation.new"
mv -f "$activation.new" "$activation"
echo 'Scrolling-gap plugin loaded in current session'
