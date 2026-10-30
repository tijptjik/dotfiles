# Tasktjik on Si

Rust/Axum runs as tasktjik, with its only writable database at
/var/lib/tasktjik/tasks.sqlite3. Dotjik manages configuration and systemd units;
Tjikup home:activate:tasktjik-api deploys the binary after home:tasktjik.
No task state belongs in Git or a writable Synctjik replica.

Tailscale Serve publishes https://si.tailb49776.ts.net/tasktjik/ privately.
Root Unix-socket peers must supply the proxy-authenticated Tailscale login
m@type.hk. Si-local clients use the same socket: UID 1000 is explicitly mapped
to m@type.hk through kernel peer credentials; supplied identity headers are
ignored for that UID. The tasktjik group permits socket access but the database
directory remains private to the service. Other identities receive 403. This application
allowlist does not modify the tailnet network ACL; narrow that separately in
the Tailscale admin policy. Funnel must stay disabled.

On an enrolled Tailscale device, run:

    tasktjik connect https://si.tailb49776.ts.net/tasktjik --notifications

This registers a revocable reminder-delivery preference and stores a local
UUID, not a password. Tailscale identity authorizes task access. Turn off a
device in the browser Devices view to stop reminders; revoke its Tailscale
membership to remove task access. Browsers do not deliver background reminders.
Fi and Li use conditional DNS only for tailb49776.ts.net; ordinary DNS remains
under the existing VPN configuration.

Synctjik app-backup includes /var/lib/tasktjik in its daily encrypted Restic
snapshots, using its online SQLite export and integrity checks. This extends
the application backup policy rather than copying live WAL files into dotfile
LFS. Restore into an isolated directory first; stop only tasktjik-api before
replacing its database, preserve tasktjik ownership and mode0700/0600, remove
stale destination WAL/SHM files, then restart. Never overwrite a running database.

Legacy JSON import is explicit and transactional:

    sudo -u tasktjik /usr/local/lib/tasktjik/tasktjik-api import-json /var/lib/tasktjik/tasks.sqlite3 DIRECTORY

Keep the original files until backup restore has been verified. No empty
fallback authority is created when HTTPS is unavailable.
