#!/usr/bin/env bash
set -euo pipefail

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
output=${1:-"$HOME/.local/lib/hypr/scrolling-gaps-local.so"}
compiler=${CXX:-c++}
flags=()
if [[ -n ${SCROLLING_GAPS_SDK_DIR:-} ]]; then
    # Optional extracted development RPMs; no system package installation needed.
    include="$SCROLLING_GAPS_SDK_DIR/usr/include"
    flags+=("-I$include" "-I$include/hyprland" "-I$include/hyprland/src" "-I$include/hyprland/protocols")
    read -r -a system_flags <<< "$(pkg-config --cflags pixman-1 libdrm cairo)"
    flags+=("${system_flags[@]}")
else
    read -r -a flags <<< "$(pkg-config --cflags hyprland)"
fi
mkdir -p -- "$(dirname -- "$output")"
build_output=$(mktemp "${output}.XXXXXX")
trap 'rm -f -- "$build_output"' EXIT
"$compiler" -std=c++23 -shared -fPIC -fno-gnu-unique -O2 -Wall -Wextra \
    -Wno-unused-parameter -Wno-missing-field-initializers \
    "${flags[@]}" "$source_dir/main.cpp" -o "$build_output"
chmod 755 "$build_output"
# Atomic replacement keeps any currently loaded inode intact.
mv -f -- "$build_output" "$output"
printf 'Built %s\n' "$output"
printf 'The plugin checks the Hyprland ABI before installing any hooks.\n'
