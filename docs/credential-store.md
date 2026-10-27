# Credential store

Fedora 45 adopted [oo7 as the replacement for GNOME Keyring](https://fedoraproject.org/wiki/Changes/oo7_Secrets_Service_Provider).
The `97-secret-service.fish` Chezmoi hook installs `oo7-daemon`, `pam_oo7`, and
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
