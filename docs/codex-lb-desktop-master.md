# Independent Codex LB instances

Both `fi` and `li` run their own Codex LB runtime on `127.0.0.1:2455`.
The laptop works without the desktop or a LAN connection. Each machine owns
its database, encryption key, account authentication and request history.
The server remains client-only.

Tjikup installs/updates the runtime on both clients. Its systemd hook disables
the former desktop reverse tunnel and stops the laptop socket proxy before
enabling the local service. The old tunnel units remain available for manual
recovery, but are no longer enabled by configuration. Runtime updates do not
restart an already-running backend; restart between active Codex sessions.

## Laptop authentication

The existing laptop database and key are preserved. An account marked
`reauth_required` needs a fresh login through the laptop's
<http://localhost:2455/dashboard>. Authenticate independently on each machine;
do not copy the desktop database or refresh tokens to bootstrap the laptop.
Sharing a refresh token between running instances can cause refresh conflicts.
Device archive synchronization does not distribute Codex LB accounts.

## Verification

On each client:

```sh
systemctl --user status codex-lb
curl --fail http://127.0.0.1:2455/health
```

On `li`, confirm `codex-lb-client.socket` and `codex-lb-client.service` are
inactive; on `fi`, confirm `codex-lb-laptop.service` is inactive. Complete a
Codex request after login to verify upstream authentication as well as local
service health.
