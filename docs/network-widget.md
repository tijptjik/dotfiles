# Networking widget

The Waybar network module toggles a standalone Quickshell panel above the clicked
module, with a 12px gap from the bar's actual top edge. The panel centers on the
network label using GTK accessibility bounds, with the click position as a
fallback, and stays within the monitor edges. The offline label stays visible so Wi-Fi can be switched back
on. Click again, press Escape, or use Close to dismiss it. The process stays
resident and polls NetworkManager every ten seconds only while open.

The panel follows Waybar's live `colors.css` palette, including Tinty updates,
with Rosé Punk fallbacks, the `tijpset` font, 10px controls, and Hyprland's 12px
outer corners and fade. Drag the Networking header to reposition it; the next
Waybar click that opens it restores the bar anchor. The surface accepts pointer
input only within the rounded panel, and keyboard focus is on demand, so the
rest of the desktop and Waybar remain interactive.

Requirements: Quickshell 0.3+, Qt Quick Controls, Python 3, NetworkManager's
`nmcli`, and `flock` (util-linux). The existing desktop polkit agent handles
privileged NetworkManager requests.
Exact label centering additionally uses Python GObject and the Atspi 2.0 typelib
(available on this Fedora desktop); it falls back to the click if unavailable.

Select a Wi-Fi network to connect or disconnect. Leave the password blank to use
a saved connection. Passwords travel over stdin, never shell commands or process
arguments, and are cleared from the field after submission or dismissal. Scan
refreshes nearby networks; Turn off/on controls the Wi-Fi radio. Ethernet
interfaces show their connection state and offer connect/disconnect controls.
Connected interfaces show local IPv4 addresses, the gateway/router, the DHCP
server that issued the lease, and DNS servers. These are read from NetworkManager;
the DHCP server is not inferred from the gateway. Address values can be selected
and copied. A static connection may have no DHCP server to report.
Hidden networks and new enterprise/802.1X profiles should be configured with
NetworkManager's connection editor first.

Sources live in `home/dot_config/quickshell/network/`. To preview from this repo:

```sh
qs -p home/dot_config/quickshell/network
qs ipc -p home/dot_config/quickshell/network call network toggle
qs ipc -p home/dot_config/quickshell/network call network close
# Or exercise the same launcher used by Waybar:
bash home/dot_config/waybar/executable_toggle-network "$PWD/home/dot_config/quickshell/network"
```

Apply through the usual chezmoi workflow, then restart Waybar to load the new
click action. Its SIGUSR2 action shows the bar; it does not reload its config.
The first click launches this configuration; later clicks use its scoped IPC
handler. No autostart entry is needed.

Run the helper's offline checks with `python3 tests/test_network_widget.py`.
