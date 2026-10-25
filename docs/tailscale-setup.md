# Tailscale for Li and Si

This runbook adds Li and Si to the existing `type.hk` tailnet for private device
connectivity and SSH. Tailscale is an additional path: keep Si's current public
SSH and HTTP routes in place until private access has been tested from another
device. Do not enable Tailscale SSH, advertise routes, select an exit node, or
change the public firewall as part of enrollment.

## Before changing Si

If no SSH session can currently be established to Si, recover access through a
trusted LAN path or local console first; Tailscale cannot be enrolled remotely
without an existing way to run commands on Si. Once reachable, do not start this
procedure over the only working SSH session. Have two SSH sessions open to Si:
keep one untouched as the fallback and use the other for setup. Verify the host
in both sessions with `hostname` before proceeding.

Use the existing `type.hk` tailnet account that Fi is already using. Do not
create or paste reusable auth keys into a shell history, repository, or chat.
Confirm that the tailnet policy permits the Fi/Li user or devices to reach Si
on TCP port 22. Do not edit the policy during this procedure if that would
remove another working access path.

## Install and start the daemon

Li and Si run Fedora. On each device, check whether the package is already
installed:

```sh
rpm -q tailscale
```

If it is absent, add Tailscale's official Fedora repository and install the
package, reviewing the DNF transaction before accepting it:

```sh
sudo dnf config-manager addrepo \
  --from-repofile=https://pkgs.tailscale.com/stable/fedora/tailscale.repo
sudo dnf install tailscale
```

On Li, Chezetc manages a `tailscaled` systemd drop-in that starts the daemon
through `mullvad-exclude`, keeping the daemon outside Mullvad while leaving
ordinary Li traffic under its existing VPN policy. Before starting the service,
check that the rendered drop-in is present:

```sh
sudo systemctl cat tailscaled
```

The effective `ExecStart` on Li should include
`/usr/bin/mullvad-exclude /usr/bin/tailscaled`. If it does not, stop here and
reconcile Li's managed Chezetc configuration and apply only that reviewed
drop-in; do not replace the unit manually. Si is a server and does not use this
client-only Mullvad override.

Start the daemon without changing SSH or firewall settings:

```sh
sudo systemctl enable --now tailscaled
sudo systemctl is-active tailscaled
```

## Enroll Li

On Li, arm a 20-minute rollback before bringing Tailscale up. The timer only
runs `tailscale down`; it does not alter SSH, firewall rules, or other routes.
If enrollment or testing stalls, it disconnects Li from the tailnet and leaves
its existing network path in place.

```sh
sudo systemd-run --unit=tailscale-rollback-li --on-active=20m \
  /usr/bin/tailscale down
sudo systemctl status tailscale-rollback-li.timer
```

Confirm the timer is waiting, then enroll using the existing tailnet account.
The CLI will print a one-time login URL; open it locally and authorize Li.

```sh
sudo tailscale up --accept-dns=false --accept-routes=false
sudo tailscale status
sudo tailscale ip -4
sudo tailscale ping fi
```

From Fi, confirm Li appears in `tailscale status` and responds to
`tailscale ping <Li-tailnet-IP>`. After those checks pass, cancel and verify
Li's rollback timer:

```sh
sudo systemctl stop tailscale-rollback-li.timer
sudo systemctl is-active tailscale-rollback-li.timer
```

The final command should report `inactive` (or `unknown` after the transient
unit is removed). If validation fails, leave the timer armed and let it expire;
do not cancel it just to retry enrollment.

## Enroll Si without risking SSH access

Only continue while the two original public SSH sessions to Si remain open.
Check that `sshd` is active and the existing public SSH session still works.
Do not change the SSH daemon, firewall, router forwarding, or DNS.

On Si, arm a 20-minute rollback and verify it is waiting before enrollment:

```sh
sudo systemd-run --unit=tailscale-rollback-si --on-active=20m \
  /usr/bin/tailscale down
sudo systemctl status tailscale-rollback-si.timer
```

Then enroll Si to the same tailnet. Authorize it through the one-time URL from
the existing account. Keep DNS and route acceptance disabled so enrollment
does not replace Si's resolver or install routes advertised by another device.

```sh
sudo tailscale up --accept-dns=false --accept-routes=false
sudo tailscale status
sudo tailscale ip -4
sudo systemctl is-active sshd
```

Record Si's Tailscale IPv4 address. From Li or Fi, test reachability and open a
**new** SSH connection over that address, while keeping both original public
SSH sessions open:

```sh
tailscale ping <Si-tailnet-IP>
ssh -o HostKeyAlias=ssh.type.hk -o StrictHostKeyChecking=yes \
  m@<Si-tailnet-IP> 'hostname; date'
```

The SSH command must report `si` and the current time without a host-key
warning. A successful ping alone is not sufficient. Also open a second fresh
SSH connection over Tailscale and verify the existing public SSH connection
still works. Confirm the public HTTP sites still load from outside the tailnet.

Only after all checks pass, cancel the Si rollback timer from the new Tailscale
SSH session and verify that it is inactive:

```sh
sudo systemctl stop tailscale-rollback-si.timer
sudo systemctl is-active tailscale-rollback-si.timer
```

Keep the original public SSH sessions open until the timer is confirmed inactive
and a fresh Tailscale SSH connection succeeds again. If any step fails, do not
cancel the timer; the automatic `tailscale down` restores the pre-enrollment
network path. Reconnect over public SSH after rollback before changing anything
else.

## After enrollment

Leave public SSH and HTTP exposure unchanged until private SSH has been stable
through a reboot and a separate-device test. Restricting public SSH is a
separate change: it needs its own timed rollback that restores the exact prior
firewall rule and must be tested while an existing public SSH session remains
open. Public HTTP services can remain on their current public routes while
administrative SSH uses Tailscale.

Tailscale SSH authentication is not enabled here; SSH continues to use the
existing OpenSSH host key and user key. Do not accept a changed host key during
testing. The `HostKeyAlias` option makes the tailnet-address test check Si
against its existing `ssh.type.hk` known-host identity.
