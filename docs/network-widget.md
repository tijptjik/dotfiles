# Networking widget

The Waybar network module previews a standalone Quickshell panel on hover above the
module, with a 12px gap from the bar's actual top edge. The panel centers on the
network label using GTK accessibility bounds, with the click position as a
fallback, and stays within the monitor edges. The offline label stays visible so Wi-Fi can be switched back
on. Hover previews close when the pointer leaves both the module and panel, with
a short delay to cross the gap. Clicking pins the panel; click the module again,
press Escape while over the panel, or use Close to dismiss it. Waybar's old tooltip
is disabled. The process stays
resident and polls NetworkManager every ten seconds only while open.

The panel follows Waybar's live `colors.css` palette, including Tinty updates,
with Rosé Punk fallbacks, the `tijpset` font, 10px controls, and Hyprland's 12px
outer corners and fade. Drag the Networking header across monitors to reposition it; the next
Waybar click that opens it restores the bar anchor. The surface accepts pointer
input only within the rounded panel. The Wayland surface is sized to the panel,
and keyboard focus is released when the pointer leaves it, so the rest of the
desktop and Waybar remain interactive.
The panel is opaque and sized to its content. Active connections appear first,
with traffic and addresses grouped in the same card; nearby Wi-Fi networks and
inactive Ethernet follow. Only the nearby Wi-Fi list scrolls; connection details,
Wi-Fi controls, and Ethernet stay visible. Icon buttons use Material Symbols
Rounded with accessible names, no focus outlines, and no tooltips.
Refresh progress replaces the Wi-Fi list temporarily without moving other sections.

Requirements: Quickshell 0.3+, Qt Quick Controls, Python 3, NetworkManager's
`nmcli`, and `flock` (util-linux). The existing desktop polkit agent handles
privileged NetworkManager requests.
Exact label centering additionally uses Python GObject and the Atspi 2.0 typelib
(available on this Fedora desktop); clicking falls back to the cursor if unavailable.
Hover previews require those accessibility bounds so other modules never open
the network panel. A small observer reads Hyprland's pointer socket and caches
bar/monitor geometry; it does not grab input or access stored network credentials.

Select a Wi-Fi network to connect or disconnect. Leave the password blank to use
a saved connection. Passwords travel over stdin, never shell commands or process
arguments, and are cleared from the field after submission or dismissal. Scan
refreshes nearby networks; Turn off/on controls the Wi-Fi radio. Ethernet
interfaces show their connection state and offer connect/disconnect controls.
Connected interfaces show local IPv4 addresses, the gateway/router, the DHCP
server that issued the lease, and default DNS servers. Addresses are read from NetworkManager;
the DHCP server is not inferred from the gateway. Address values can be selected
and copied. A static connection may have no DHCP server to report.
Default DNS comes from systemd-resolved, respecting VPN catch-all routing such as
Mullvad's `~.` domain. More-specific split-DNS domains can use other resolvers.
If resolved is unavailable, the row is labelled Link DNS and shows the adapter's
configured servers instead.

Download/upload speeds are sampled once per second from Linux interface byte
counters, using measured monotonic time. The transferred total is received plus
sent data, displayed first alongside download and upload speeds. It counts
since that adapter's counters were reset (usually at boot or device
creation), not a monthly allowance or the current Wi-Fi session. It includes LAN
traffic. Each physical interface is displayed separately to avoid double-counting
VPN/tunnel counters. Counter resets and the first sample show no rate until a
fresh interval is available. Traffic sampling stops while the panel is closed;
kernel totals keep counting.
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
