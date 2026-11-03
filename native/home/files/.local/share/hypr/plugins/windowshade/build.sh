#!/usr/bin/env bash
set -euo pipefail
# Select a reviewed upstream release and local patch from the build headers.
# Never fall back to upstream HEAD for compositor hooks.
flags="-shared -fPIC -O2 -std=c++23 -fno-gnu-unique"
if [[ -n ${HYPRWINDOWSHADE_SDK_DIR:-} ]]; then
    include="$HYPRWINDOWSHADE_SDK_DIR/usr/include"
    flags+=" -I$include -I$include/hyprland -I$include/hyprland/src -I$include/hyprland/protocols $(pkg-config --cflags pixman-1 libdrm cairo)"
else
    flags+=" $(pkg-config --cflags hyprland lua)"
fi
read -r -a header_flags <<< "$flags ${CPPFLAGS:-}"
commit=$(printf '#include <hyprland/src/version.h>\nGIT_COMMIT_HASH\n' | "${CXX:-c++}" "${header_flags[@]}" -E -P -x c++ - | tail -n 1 | tr -d '"')
case "$commit" in
    efb50993780079460b0cbed1363e2166a2de1d9f)
        revision=a4c6b8af424a189072427c4c90ef2938e1b481d3
        isolation_patch=chat-render-isolation.patch ;;
    0aa6745f705f2c4b0a5004eb019ef76e5bbdb426)
        revision=0766b631a18a532c094d25ae6b6fcc242545aafe
        isolation_patch=chat-render-isolation-0.57.patch ;;
    *) printf 'No reviewed WindowShade build for Hyprland commit %s\n' "$commit" >&2; exit 1 ;;
esac
cache="${XDG_CACHE_HOME:-$HOME/.cache}/hypr-windowshade"
output="${1:-$HOME/.local/lib/hypr/HyprWindowShade.so}"
mkdir -p "$cache" "$(dirname -- "$output")"
if [[ ! -d "$cache/upstream/.git" ]]; then
    git clone --no-checkout https://github.com/ManofJELLO/HyprWindowShade "$cache/upstream"
fi
git -C "$cache/upstream" cat-file -e "$revision^{commit}" 2>/dev/null || git -C "$cache/upstream" fetch origin "$revision"
build_dir=$(mktemp -d "$cache/build.XXXXXX")
trap 'rm -rf -- "$build_dir"' EXIT
git -C "$cache/upstream" archive "$revision" | tar -x -C "$build_dir"
patch --fuzz=0 -d "$build_dir" -p1 < "$(dirname -- "${BASH_SOURCE[0]}")/$isolation_patch"
# Reject mismatched internal ABIs before upstream installs any rendering hooks.
python3 - "$build_dir/main.cpp" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
source = path.read_text()
needle = '    PHANDLE = handle;'
assert source.count(needle) == 1
path.write_text(source.replace(needle, needle + '''
    if (std::string(__hyprland_api_get_hash()) != __hyprland_api_get_client_hash())
        throw std::runtime_error("HyprWindowShade: rebuild for this Hyprland ABI");''', 1))
PY
# CPPFLAGS can supply additional extracted glslang/Lua development headers.
make -C "$build_dir" CXXFLAGS="$flags ${CPPFLAGS:-}"
install -m 755 "$build_dir/HyprWindowShade.so" "$output.new"
mv -f "$output.new" "$output"
printf 'Built %s from %s (not loaded).\n' "$output" "$revision"
