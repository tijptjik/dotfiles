#!/usr/bin/env bash
# Temporary, reproducible GTK-only repair for Transmission 4.1.3's favicon race.
set -euo pipefail
case "$(hostname -s)" in
    fi|li) ;;
    *) echo 'This repair is only for the Fi/Li GTK desktop clients; never Si.' >&2; exit 2 ;;
esac
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
version=4.1.3
revision=4.1.3-favicon1
expected=ce7d2d8b101f7eb54bc3cf0bc55f52f7ebd4a25fa48e00bdca9a7e0fc02617da
prefix="$HOME/.local/opt/transmission-gtk/$revision"
launcher="$HOME/.local/bin/transmission-gtk"
desktop="$HOME/.local/share/applications/transmission-gtk.desktop"
patch_file="$repo/patches/transmission-4.1.3-favicon-worker.patch"
if [[ -e "$launcher" && ! -L "$launcher" ]]; then
    echo "Refusing to replace an unmanaged executable: $launcher" >&2
    exit 1
fi
if [[ -e "$desktop" ]] && ! grep -qx 'X-Tjikup-Transmission-Repair=true' "$desktop"; then
    echo "Refusing to replace an unmanaged desktop entry: $desktop" >&2
    exit 1
fi
# Fail before downloading if the reviewed development dependencies are missing.
pkg-config --exists gtkmm-4.0 libcurl libevent
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
archive="$work/transmission.tar.xz"
if [[ -n "${TRANSMISSION_SOURCE_ARCHIVE:-}" ]]; then
    cp -- "$TRANSMISSION_SOURCE_ARCHIVE" "$archive"
else
    curl --fail --location --retry 2 --connect-timeout 15 --max-time 180 \
        "https://github.com/transmission/transmission/releases/download/$version/transmission-$version.tar.xz" -o "$archive"
fi
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
tar -xJf "$archive" -C "$work"
source_dir="$work/transmission-$version"
patch --batch --forward --directory "$source_dir" -p1 < "$patch_file"
cp -- "$repo/tests/fixtures/transmission/favicon-lifetime.cc" "$source_dir/favicon-lifetime.cc"
cat >> "$source_dir/CMakeLists.txt" <<'CMAKE'

add_executable(favicon-lifetime favicon-lifetime.cc)
target_include_directories(favicon-lifetime PRIVATE "${PROJECT_SOURCE_DIR}" "${PROJECT_BINARY_DIR}")
target_link_libraries(favicon-lifetime PRIVATE ${TR_NAME})
CMAKE
cmake -S "$source_dir" -B "$work/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DENABLE_GTK=ON -DUSE_GTK_VERSION=4 -DENABLE_QT=OFF \
    -DENABLE_DAEMON=OFF -DENABLE_UTILS=OFF -DENABLE_CLI=OFF \
    -DENABLE_TESTS=OFF -DINSTALL_WEB=OFF -DRUN_CLANG_TIDY=OFF
cmake --build "$work/build" --parallel 4
# A loopback-only regression: no saved torrents, credentials or daemon involved.
timeout 25 env -u http_proxy -u https_proxy -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    NO_PROXY='*' no_proxy='*' "$work/build/favicon-lifetime" "$work/regression-cache"
DESTDIR="$work/stage" cmake --install "$work/build"
"$work/stage$prefix/bin/transmission-gtk" --version
install -d -m 755 "$(dirname -- "$prefix")" "$(dirname -- "$launcher")"
if [[ -e "$prefix" ]]; then
    mv -- "$prefix" "$prefix.previous-$(date -u +%Y%m%dT%H%M%SZ)"
fi
mv -- "$work/stage$prefix" "$prefix"
{
    printf 'Source: Transmission %s\nArchive-SHA256: %s\n' "$version" "$expected"
    sha256sum "$patch_file" "$prefix/bin/transmission-gtk"
} > "$prefix/repair-receipt.txt"
ln -sfn -- "$prefix/bin/transmission-gtk" "$launcher.new"
mv -Tf -- "$launcher.new" "$launcher"
# Session services may not include ~/.local/bin in PATH. Pin all menu actions.
install -d -m 755 "$(dirname -- "$desktop")"
sed -e "s|^Exec=transmission-gtk|Exec=\"$launcher\"|" \
    -e "s|^TryExec=transmission-gtk$|TryExec=$launcher|" \
    "$prefix/share/applications/transmission-gtk.desktop" > "$desktop.new"
printf '\nX-Tjikup-Transmission-Repair=true\n' >> "$desktop.new"
chmod 644 "$desktop.new"
mv -Tf -- "$desktop.new" "$desktop"
printf 'Installed desktop-only repair: %s\n' "$launcher"
