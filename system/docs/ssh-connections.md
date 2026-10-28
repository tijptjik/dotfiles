# SSH connection reuse

Chezetc installs `/etc/ssh/ssh_config.d/10-connection-reuse.conf` on Fi, Li,
and Si. OpenSSH clients automatically share authenticated connections and keep
an idle master alive for five minutes. This covers Git over SSH, terminal SSH,
SCP/SFTP, fleet shortcuts, and tools that invoke OpenSSH. Clients with their own
SSH implementations do not inherit OpenSSH configuration.

Control sockets live at `~/.ssh/cm-%C`, inside each local user's SSH directory.
Keep that directory writable only by its owner. OpenSSH hashes the local host,
destination host, port, remote user, and jump host into `%C`; different endpoints
and accounts do not share sockets. The first request still authenticates
normally. Subsequent requests reuse the authenticated transport, and idle
masters expire automatically. No SSH daemon reload is needed.

Apply just this client policy, without running unrelated hooks:

```sh
chezetc apply --exclude=scripts /etc/ssh/ssh_config.d/10-connection-reuse.conf
ssh -G git@github.com | rg '^control(master|path|persist) '
```

Expected settings are `controlmaster auto`, `controlpersist 300`, and a control
path under `~/.ssh/cm-`. Per-user configuration and command-line options take
precedence over these system defaults.

To check or retire a master, use the same destination and options as the
original command:

```sh
ssh -O check git@github.com
ssh -O stop git@github.com
```

`stop` stops accepting new shared sessions without interrupting existing ones.
For an independent connection, use both `-o ControlMaster=no` and
`-o ControlPath=none`. This is appropriate for systemd-supervised tunnels whose
connection and forwarding lifetime must belong to the service. The retained
Codex laptop tunnel unit has this explicit override.

Reused sessions retain the master's network route and authentication context.
Use an independent connection when testing a different VPN route, identity,
or host-key policy for the same endpoint. OpenSSH may fall back to a fresh
connection if simultaneous first requests race to create a master; later
requests reuse the winner.

## Terminal environment

The managed SSH client exports `COLORTERM`, `TERM_PROGRAM`, and `HERDR_ENV`
when they exist in the originating environment. The managed server accepts the
same variables. Herdr sets `TERM_PROGRAM=herdr` and `HERDR_ENV=1` itself; do not
set those globally in Fish, since other terminals need their own identity.
OpenSSH forwards `TERM` separately when allocating a PTY.

This lets remote Tjikup select Herdr colour icons instead of its compact glyph
fallback. Both the client `SendEnv` and server `AcceptEnv` policies must be
installed. The server policy is managed on Si; Fi and Li exclude server SSH
configuration from Chezetc.

Apply only the affected files, without unrelated hooks:

```sh
# On the originating machine:
chezetc apply --exclude=scripts /etc/ssh/ssh_config.d/50-redhat.conf
ssh -G m@ssh.type.hk | rg '^sendenv '

# On Si:
chezetc apply --exclude=scripts /etc/ssh/sshd_config.d/50-redhat.conf
sudo sshd -t && sudo systemctl reload sshd
```

Start a new SSH session after applying the policy. Existing remote shells keep
their original environment. If a reused connection retains the old policy, use
`ssh -o ControlPath=none` for a fresh transport. In the remote shell, verify
`printenv TERM TERM_PROGRAM HERDR_ENV`; from Herdr it should include
`xterm-256color`, `herdr`, and `1`.
