# Codex through Mullvad on Si

Si's `codex-vpn-network.service` creates a dedicated network namespace with only
loopback and a Mullvad WireGuard interface. The interface's encrypted UDP socket
belongs to the host namespace. No host routes, DNS, firewall rules or other
services are modified. No virtual Ethernet connection provides an escape route.
Only explicitly attached services use this namespace.

The system manifest group `codex-vpn` owns the units, account declaration and
private configuration directory. WireGuard tools are a server RPM dependency.
The official npm Codex CLI is installed independently in `/opt/codex-vpn`, owned
by root; the initial deployment installed version 0.170.0 with lifecycle scripts
disabled. Keep this runtime separate from the desktop Codex LB instances.

## Private prerequisites

The Singapore endpoint `sg-sin-wg-001` is stored in the `dotfiles` Bitwarden
Secrets Manager project as `SI_CODEX_MULLVAD_WIREGUARD` (secret ID
`0537f34a-4616-4eb9-bc1e-b506008f6eff`). Only the secret reference is in Git.
The Si-only credential manifest retrieves the complete downloaded configuration:

```sh
/usr/local/lib/tjikup/tjikup files apply \
  --manifest native/home/si.json \
  --state-dir /home/m/.local/state/tjikup/files/home --group codex-vpn
```

Run this as `m` on Si, using its existing BWS machine token. The directory is
0700 and configuration 0600. A failed BWS lookup prevents application. Credential
rotation requires reviewing the private source change, then refreshing the root
runtime inputs below and restarting the namespace during an idle period.

Generate a dedicated Mullvad WireGuard configuration for Si. Do not reuse an
active device's private key or put the downloaded configuration in Git. Stage it
at `/home/m/.config/codex-vpn/mullvad.conf`, directory mode 0700 and file mode 0600. Do not print its contents into logs or chat.

Before activation, an administrator must prepare these root-owned private files:

- `/etc/codex-vpn/wireguard.conf` (0600): the WireGuard-native configuration,
  produced with `wg-quick strip` from the downloaded file. Use a numeric peer
  endpoint so initial DNS does not depend on a tunnel that is not up yet.
- `/etc/codex-vpn/address.env` (0600): `WIREGUARD_ADDRESS=` followed by the
  assigned IPv4 CIDR from that configuration. This unit deliberately configures
  IPv4 only; it does not provide an IPv6 escape route.
- `/etc/codex-vpn/resolv.conf`: the supplied default is Mullvad's `10.64.0.1`.
  Confirm that this matches the downloaded configuration before activation.

Check the peer permits `0.0.0.0/0`. Do not run `wg-quick up` on the host.
`wg-quick strip` removes its routing, DNS and hook directives; none are executed.

Apply only the manifest group using the existing native system state directory:

```sh
sudo /usr/local/lib/tjikup/tjikup files plan \
  --manifest system/native/si/manifest.json --state-dir /var/lib/tjikup/files --group codex-vpn
sudo /usr/local/lib/tjikup/tjikup files apply \
  --manifest system/native/si/manifest.json --state-dir /var/lib/tjikup/files --group codex-vpn
sudo systemd-sysusers /etc/sysusers.d/codex-vpn.conf
sudo systemctl daemon-reload
sudo systemctl start codex-vpn-network.service
```

The existing native system state is `/var/lib/tjikup/files`; do not invent a second
state directory for these destinations. Never blanket-apply system policy for
this change. The namespace service is enabled for boot only after verification.

## Subscription authentication and request

Authenticate the dedicated account independently. Never copy desktop Codex LB
databases, keys or refresh tokens. Run device login in a transient system unit
with the same networking and DNS as the check service:

```sh
sudo systemd-run --unit=codex-vpn-login --collect --wait --pipe \
  --property=User=codex-vpn --property=Group=codex-vpn \
  --property=BindsTo=codex-vpn-network.service \
  --property=After=codex-vpn-network.service \
  --property=NetworkNamespacePath=/run/netns/codex-vpn \
  --property=BindReadOnlyPaths=/etc/codex-vpn/resolv.conf:/etc/resolv.conf \
  --property=BindReadOnlyPaths=/etc/codex-vpn/nsswitch.conf:/etc/nsswitch.conf \
  --property='InaccessiblePaths=-/run/nscd/socket -/run/systemd/resolve' \
  --property=StateDirectory=codex-vpn --property=StateDirectoryMode=0700 \
  --property=UMask=0077 --property=NoNewPrivileges=yes \
  --setenv=HOME=/var/lib/codex-vpn --setenv=CODEX_HOME=/var/lib/codex-vpn \
  --setenv=PATH=/usr/bin:/bin \
  /opt/codex-vpn/bin/codex login --device-auth
sudo systemctl start codex-vpn-check.service
sudo cat /var/lib/codex-vpn/last-check.txt
```

The last command must return `CODEX_SI_OK`. A healthy tunnel, CLI version, or
successful login alone does not prove inference works. Keep the device code
private and complete its browser flow before expiry.

## Acceptance and rollback

Record the host default routes and ordinary egress before and after activation.
Check Mullvad's connection endpoint from inside the service namespace using its
DNS mount; ordinary host traffic must retain its original route. Inspect only
WireGuard handshake timestamps and byte counts, never `wg showconf` or private
keys. Verify DNS and IPv4 egress through the tunnel and lack of IPv6 egress.

Temporarily lower the namespace's WireGuard link and confirm an egress request
fails, while a host request still works. Restore the link, confirm recovery,
then run the Codex smoke request. Finally test service stop/start and ensure
there are no leftover host interfaces or routes. Do this before enabling boot
startup or attaching Atlas jobs. A stopped VPN must never trigger a direct
network retry.

To stop this feature, stop `codex-vpn-check.service` and disable/stop
`codex-vpn-network.service`. Its cleanup deletes only `cvpn-si` and the
`codex-vpn` namespace. Keep authentication and VPN credentials for recovery;
removing them is a separate explicit operation. Reserve those interface and
namespace names for this unit.

Atlas migration and CF/Si benchmarking follow successful inference validation.
The existing Atlas integration is an image-generation API, so compare equivalent
images, prompts and caching conditions; a text smoke test is not that benchmark.
