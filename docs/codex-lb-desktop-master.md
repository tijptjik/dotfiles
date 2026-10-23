# Codex LB desktop master

`fi` owns the accounts, encryption key, token refreshes and request history.
`li` uses its existing `http://127.0.0.1:2455` endpoint through an SSH reverse
tunnel maintained by `codex-lb-laptop.service` on `fi`. Only loopback is bound
on both machines; the desktop does not need an SSH server. On the laptop,
`codex-lb-client.socket` and systemd's socket proxy relay port 2455 to the
tunnel at port 42455. The high tunnel port works with Fedora's existing
SELinux SSH policy without changing policy or disabling enforcement.

The tunnel connects to `io@li.local`, verifies the pinned laptop SSH host key,
and uses existing SSH authentication. It retries every ten seconds after
disconnects. Both machines must be awake and reachable on the same LAN, with
mDNS and laptop SSH available. Off-LAN access is not configured. When the
desktop is unavailable, laptop Codex requests fail rather than using stale
local credentials.

The laptop's old database and key remain untouched. Its local service is
disabled, and `ConditionHost=fi` prevents it from being started accidentally.
Account changes made through the laptop dashboard now change the desktop's
accounts. This is one shared backend, not account backup or replication.

Check on the desktop:

```sh
systemctl --user status codex-lb codex-lb-laptop
journalctl --user -u codex-lb-laptop -n 30
```

To undo, stop and disable `codex-lb-laptop` on the desktop and
`codex-lb-client.socket` on the laptop, stop `codex-lb-client.service`, remove the
`ConditionHost=fi` restriction from the laptop's local unit, reload systemd
and enable its local `codex-lb` service. Its old account still requires login.
