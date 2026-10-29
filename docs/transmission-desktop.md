# Transmission desktop repair

Fi/Li use the GTK desktop client. Si uses the LinuxServer daemon container,
shared downloads, Unpackerr and the host-bound cleanup timer. This repair is
restricted to Fi/Li; it does not change Si's image, RPC configuration or jobs.

## Failure and fix

Fi's Fedora Transmission 4.1.3-2.fc45 aborted with `Resource deadlock avoided`.
The core traced `std::thread::join()` through `tr_web::~tr_web()` and
`FaviconCache::InFlightData`: the last favicon response could destroy its own
web worker on that worker's thread.

`patches/transmission-4.1.3-favicon-worker.patch` moves worker ownership to the
UI-owned favicon cache. One lazily created worker serves the cache and is joined
before its mediator and cache are destroyed. The regression fixture in
`tests/fixtures/transmission/favicon-lifetime.cc` uses only a closed loopback
endpoint. The unpatched version aborts with the original exception; the patched
version exits successfully. No torrents or private profile are needed for it.

## Install

This is a local, pinned repair, not a new upstream release. Build dependencies
on Fedora include CMake, Ninja, a C++ compiler, gettext, `gtkmm4.0-devel`,
`libcurl-devel`, `libevent-devel`, `libnatpmp-devel` and `miniupnpc-devel`.

```sh
bash scripts/install-transmission-desktop.sh
```

The installer verifies the official 4.1.3 archive SHA256, applies the patch,
builds only the GTK client and its regression fixture, runs the fixture, then
stages installation under `~/.local/opt/transmission-gtk/4.1.3-favicon1`.
`TRANSMISSION_SOURCE_ARCHIVE` can supply an already downloaded archive; the
same digest check still applies. The prefix contains `repair-receipt.txt` with
source, patch and binary hashes. Reinstalling preserves the previous prefix.

`~/.local/bin/transmission-gtk` points to the repaired binary. A user desktop
entry pins its normal, paused and minimized actions to that launcher because
Fi's user-service PATH omits `~/.local/bin`. Unmanaged executables and desktop
entries are refused. No torrent/profile data is installed or removed.

## Rollback and retirement

Remove only the repair's launcher symlink and desktop override to return to the
packaged client:

```sh
rm ~/.local/bin/transmission-gtk
rm ~/.local/share/applications/transmission-gtk.desktop
```

Check that the symlink and desktop entry are still repair-owned first; the
entry contains `X-Tjikup-Transmission-Repair=true`. Keep the private prefix until
rollback is no longer needed. A package upgrade does not override this local
repair automatically: retire it after a fixed packaged version passes the
lifetime regression and desktop acceptance checks.

## Validation boundary

The installer and loopback regression passed on Fi. A fresh synthetic profile
and the backed-up real profile both ran with transfers paused and exited with
status 0. The real window was mapped, and `/proc/PID/exe` confirmed the repaired
binary. These were brief launches; sustained operation and user visual approval
remain separate. No new Transmission core dump appeared during these checks.
The private profile backup remains under
`~/.local/state/tjikup/transmission-desktop-before-fix`.

Policy tests render Fi,
Li and Si independently and prove that desktop settings do not replace Si's
daemon settings. Si's startup hook retains RPC identity and server download
policy. Li has not received the binary, and Si's services were not changed.
