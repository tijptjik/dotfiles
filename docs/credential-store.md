# Credential store

Fedora 45 adopted [oo7 as the replacement for GNOME Keyring](https://fedoraproject.org/wiki/Changes/oo7_Secrets_Service_Provider).
The `97-secret-service.fish` Tjikup hook installs `oo7-daemon`, `pam_oo7`, and
`oo7-portal` on fi, li, and si. It removes the superseded `gnome-keyring` and
`gnome-keyring-pam` packages with dependency cleanup disabled, stops this user's
old daemon, and enables the oo7 user service. This removes the competing D-Bus
activation and login startup paths that otherwise cause `Zbus(NameTaken)`.

Existing files in `~/.local/share/keyrings` are retained. oo7 migrates legacy
keyrings when unlocked; encrypted keyrings may need their password on first
access or the next password login. Fedora's GDM PAM configuration already
includes `pam_oo7`. Other login managers and headless sessions may require manual
unlocking; enabling the service alone does not prove the keyring is unlocked.
The hook never reads passwords or exports secrets.

Verify the provider with `busctl --user status org.freedesktop.secrets` and
`systemctl --user status oo7-daemon.service`. Inspect migration or startup issues
with `journalctl --user -u oo7-daemon.service`. A remaining `Zbus(NameTaken)` can
indicate a different manually configured provider; the hook does not terminate
arbitrary Secret Service implementations.

## Runtjik AMO signing

Fi owns `~/.config/runtjik/amo.env` through `native/home/fi.json`, group
`runtjik-amo`. Its template references the BWS `RUNTJIK_AMO_API_KEY` and
`RUNTJIK_AMO_API_SECRET` entries in the dotfiles project. Only secret IDs belong
in Git. The rendered POSIX environment file is sensitive, mode 0600, and uses
single-quote escaping so credentials are never interpreted as shell commands.
Li, Si and portable devices are not enrolled for extension publishing.

Normal `dotjik apply` includes this file. To check or apply only AMO credentials,
without rendering unrelated secrets:

```sh
tjikup workflow files credentials check --group runtjik-amo
tjikup workflow files credentials apply --group runtjik-amo
dotjik source-path ~/.config/runtjik/amo.env
```

The normal encrypted BWS cache applies. After rotating either BWS entry, refresh
this group with `TJIKUP_REFRESH_SECRETS=all` in the environment; the group filter
limits resolution to the two AMO entries. This does not submit an AMO release.
For signing, export the managed values in a Bash subprocess:

```sh
bash -c 'set -a; . "$HOME/.config/runtjik/amo.env"; set +a; cd "$HOME/code/tjikos"; bun run --cwd apps/runtjik browser:sign:listed'
```

Keep credentials out of terminal logs and do not use shell tracing when loading
or signing. The API key is the AMO JWT issuer; the API secret is its JWT secret.
