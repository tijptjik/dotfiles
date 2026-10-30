# Tailscale and fleet SSH

## Everyday access on Fi and Li

Fi and Li keep their enrolled tailnet connections up, including after boot and
desktop unlock. `tailscaled` is enabled at boot and persists `WantRunning=true`
after `tailscale up`. The lock wrapper and application provisioning hooks no
longer disconnect it. Tjikup converges this policy for both client machines.
An expired login still requires interactive enrollment; the shortcuts never
create a new enrollment automatically.

```fish
sshfi                         # connect to Fi
sshli                         # connect to Li
sshli hostname                # run a remote command
fleet-ssh --transport lan li hostname
fleet-ssh --transport tailnet fi hostname
```

The shortcuts call `~/.local/bin/fleet-ssh`. It starts the local daemon with
noninteractive sudo if needed and resumes a stopped, enrolled tailnet. It reads
the local Tailscale peer map, prefers tailnet IPv6, and falls back to Avahi LAN
discovery over IPv6 then IPv4. Link-local IPv6 addresses retain their interface
scope. It never hardcodes DHCP addresses or requires MagicDNS to replace Mullvad
DNS. `fitjikup` and `litjikup` use the same resolver.

Mullvad remains connected with LAN sharing enabled. Fi runs tailscaled through
Mullvad because its excluded route cannot reach coordination. Li retains its
split-tunnel policy; ordinary traffic keeps its existing VPN policy. Tailscale
DNS and advertised-route acceptance are disabled on both clients. IPv6 tailnet
addresses are within Mullvad's permitted local ULA range; IPv4 tailnet addresses
are in CGNAT space and may be blocked even with LAN sharing enabled.

The helper probes TCP port 22 before selecting a route, then executes OpenSSH
exactly once. Authentication errors and remote-command failures do not trigger a
retry. OpenSSH checks the same pinned `fi.local` or `li.local` host identity on
every transport, using `~/.config/fleet-ssh/known_hosts` and the user's existing
known-hosts file. This is ordinary OpenSSH, not Tailscale SSH. The remote device
must be awake with its SSH server and tailnet available; the helper cannot wake
or reconnect an unreachable remote device.

Existing Fish sessions that loaded the old hardcoded `sshfi` alias can run
`functions -e sshfi sshli` to use the new autoloaded functions.

## Enrollment

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

Check the actual SSH transport before assuming Si is down. On 2026-10-29,
Fi reached Si's pinned public SSH endpoint through Mullvad, while the old
`mullvad-exclude ssh` route timed out. Ordinary SSH with the same pinned identity
is a valid fallback:

```sh
ssh -x -o HostKeyAlias=ssh.type.hk -o StrictHostKeyChecking=yes m@ssh.type.hk
```

Fi's split-excluded `tailscaled` process also could not reach the coordination
server on that network. Routing only that process through the existing VPN
restored coordination. Treat this as a network-dependent diagnostic result,
not authorization to disable Mullvad or change every application's routing.

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

On Li, Tjikup manages a `tailscaled` systemd drop-in that starts the daemon
through `mullvad-exclude`, keeping the daemon outside Mullvad while leaving
ordinary Li traffic under its existing VPN policy. Before starting the service,
check that the rendered drop-in is present:

```sh
sudo systemctl cat tailscaled
```

Fi uses `/usr/sbin/tailscaled` directly, retaining `$FLAGS`, so coordination
uses Mullvad. The effective `ExecStart` on Li should include
`/usr/bin/mullvad-exclude /usr/bin/tailscaled`. If it does not, stop here and
reconcile Li's managed Tjikup configuration and apply only that reviewed
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

## Enroll Si with a ten-minute automatic disconnect

Keep two existing trusted SSH sessions to Si open: one untouched fallback and
one for setup. Record nginx's state before enrollment and confirm the public
sites load from outside the tailnet. Do not change nginx, sshd, firewall rules,
router forwarding, or DNS, and do not run a broad Tjikup apply for enrollment.

```sh
hostname
sudo systemctl show nginx -p ActiveState -p SubState -p MainPID -p ExecMainStartTimestamp
sudo nginx -t
sudo systemctl is-active sshd
```

Arm a ten-minute rollback and verify it is waiting **before** bringing Tailscale
up. This transient systemd timer activates a service that runs `tailscale down`.
It remains armed even when enrollment succeeds. The countdown starts when the
timer is armed, so authentication time is included.

**A pending browser approval can outlive this timer.** On 2026-10-29, completing
login after `tailscale down` had already run brought Si online again. Do not
complete an old approval after the deadline. If enrollment is still pending at
expiry, stop `tailscaled` over the original SSH route before leaving the trial;
for an unattended enrollment timeout, the expiry action must also stop the
daemon. The `tailscale down` timer alone is not a bound on a late login callback.
If late approval already brought the node online, disconnect it, verify the
original route, and arm a fresh timer before testing the enrolled connection.
Completed enrollment is retained; the fresh connection test needs no browser
approval.

```sh
sudo systemd-run --unit=tailscale-rollback-si --on-active=10m \
  --timer-property=AccuracySec=1s /usr/bin/tailscale down
sudo systemctl show tailscale-rollback-si.timer \
  -p ActiveState -p SubState -p NextElapseUSecMonotonic -p Triggers
sudo systemctl show tailscale-rollback-si.service -p ExecStart
```

Require `ActiveState=active`, `SubState=waiting`, and the expected service command
before proceeding. If arming or inspection fails, do not bring Tailscale up.
Do not re-arm the timer to extend a failed test while the connection is uncertain.

Then enroll Si in the existing `type.hk` tailnet using its one-time login URL.
Keep DNS and route acceptance disabled, Tailscale SSH off, and no exit node or
advertised subnet routes. Inspect existing preferences first if Si was enrolled
previously; do not silently inherit an exit-node or subnet-router configuration.

```sh
sudo tailscale up --accept-dns=false --accept-routes=false
sudo tailscale status
sudo tailscale ip -6
sudo tailscale ip -4
sudo systemctl is-active sshd
```

From Fi or Li, open a **new** connection to Si's reported tailnet IPv6 address
(IPv4 is a fallback if reachable). Preserve Si's existing pinned SSH identity:

```sh
tailscale ping <Si-tailnet-IP>
ssh -o ControlMaster=no -o ControlPath=none \
  -o HostKeyAlias=ssh.type.hk -o StrictHostKeyChecking=yes \
  m@<Si-tailnet-IP> 'hostname; date'
```

Require `si` and the current time without a host-key warning. Also verify a
second fresh tailnet SSH connection and the original SSH route. Repeat the nginx
state/configuration checks above: the master PID and start time should be
unchanged. Check the public HTTP sites again from outside the tailnet.

**Leave the timer armed.** After ten minutes, use the original SSH route to
verify the journal records the rollback service's actual execution and success,
and Tailscale reports `Stopped`. If enrollment never completed, it may instead
report `NeedsLogin`; in either case require `WantRunning=false`. Transient units
may already have been collected, so an empty `systemctl show` result or its
default success status alone is not execution evidence:

```sh
sudo systemctl show tailscale-rollback-si.service -p Result -p ExecMainStatus
sudo journalctl -u tailscale-rollback-si.service --no-pager -n 10
sudo tailscale status --json
sudo tailscale debug prefs | jq '{WantRunning}'
sudo systemctl show nginx -p ActiveState -p SubState -p MainPID -p ExecMainStartTimestamp
```

Verify public HTTP and fresh original-route SSH again after disconnection.
`tailscale down` preserves enrollment but disconnects the tailnet; it does not
undo unrelated network changes. Do not re-enable Si's tailnet or deploy a hook
that reconnects it during this trial. Persistent connectivity is a subsequent
explicit decision. No backup depending on this temporary route should start if
it could outlast the ten-minute window.

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

## Si trial evidence — 2026-10-29

Tailscale 1.98.8 was already installed and its daemon active, so no Tjikup/Dotjik
rollout or daemon restart was needed. A transient `tailscale-rollback-si.timer`
was armed at 19:44:29 HKT before `tailscale up`, with DNS/route acceptance and
Tailscale SSH disabled. Enrollment reached the interactive login step but did
not complete. The system journal records automatic `tailscale down` at
19:54:29 and successful completion at 19:54:30; `WantRunning=false` was verified.
At that point Si remained `NeedsLogin`, so tailnet membership and tailnet SSH
were unproven. The later completed-enrollment trial is recorded below.

Existing SSH sessions and a fresh post-rollback public SSH connection worked.
nginx's master/worker PIDs and start times were unchanged, and `nginx -t` passed
before and after. Repeated public probes of home/read/listen returned HTTP 200;
music retained HTTP 302. This proves the observed trial and rollback did not
interrupt those routes; it does not prove behavior after successful enrollment.
Fi's temporary process-specific VPN routing change was restored afterward.
Finish authentication and repeat a newly guarded connection test before relying
on Si's tailnet path. No backup or restore was run as part of this trial.

## Completed Si enrollment and connection trial — 2026-10-29

Si is enrolled in the existing `type.hk` tailnet. A login approved after the
22:15:08 rollback brought it online again; it was explicitly disconnected at
22:24:23 before the already-enrolled connection test. This is the late-approval
case described above, not a failure of systemd to execute the earlier timer.

The fresh `tailscale-rollback-si-20261029-2224.timer` was armed at 22:25:22 HKT
before reconnecting Si. The peer map reported Si online in the correct tailnet;
a Tailscale ping and two fresh IPv6 OpenSSH connections passed with Si's existing
pinned host key and connection sharing disabled. Both original SSH sessions and
a fresh public SSH session remained usable. DNS/route acceptance, Tailscale SSH,
exit-node selection and subnet advertisement remained disabled.

The journal records automatic `tailscale down` at 22:35:22 and successful
completion at 22:35:23. Si then reported `Stopped` and `WantRunning=false`; Fi
reported it offline, and a fresh tailnet SSH connection timed out. Enrollment
is retained. Si was left disconnected as requested; persistent connectivity has
not been enabled.

nginx's master and all eight workers kept their existing PIDs/start times, and
`nginx -t` passed before and after. Periodic checks during the connection and
after disconnect returned HTTP 200 for home/read/listen and HTTP 302 for music.
A fresh post-disconnect public SSH connection passed. No nginx configuration,
firewall, Docker service or backup job was changed by the trial. These are
observed availability checks, not a claim of continuous packet-level monitoring.
Fi's temporary tailscaled process-routing adjustment was restored afterward.

Regular tailnet operation still needs Fi's coordination-route policy reconciled
with the working VPN transport. The excluded route was unhealthy; the temporary
in-VPN route worked. No persistent Fi networking policy was changed. Synctjik
is installed with protection capabilities on Fi, but Si still lacks both user
and root-owned Synctjik binaries and retains the old Drive service routing.
Backup deployment and actual backup/restore acceptance remain separate steps.

## Fi with Mullvad

Tjikup's `system:tailscale` recipe enables `tailnet-mullvad.service` after native
system-file deployment. Fi's manifest owns the unit and `/etc/tailnet-mullvad.nft`.
Priority 5200 routes only tailnet IPv4/IPv6 ranges through Tailscale table 52,
ahead of Mullvad's catch-all route. Firewall exceptions require the `tailscale0`
interface and tailnet source/destination ranges. They run after Tailscale's
mangle connection-mark save and before Mullvad's filter, using Mullvad's existing
split-tunnel mark contract. Ordinary internet traffic retains Mullvad protection.
The service's reload atomically replaces only its own nftables table. Stop removes
only its exact route rules and table. Mullvad and Tailscale updates should be
followed by direct tailnet SSH, `sshsi`, and ordinary route checks.

Verification on Fi: `ip route get 100.85.220.100` must use `tailscale0`, while
`ip route get 1.1.1.1` must use the Mullvad interface when connected. Verify SSH
with the existing trusted `ssh.type.hk` host-key identity; do not accept a new
key simply because the transport address changed. `sshsi` remains the configured
`mullvad-exclude ssh -x m@ssh.type.hk` public endpoint. MagicDNS is intentionally
disabled, so bare `si` is not a system DNS name.
