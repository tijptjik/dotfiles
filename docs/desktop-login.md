# Desktop login and credential-store unlocking

Fi and Li use GDM autologin into Hyprland, followed by Hyprlock. GDM remains
only the session launcher; its password screen is bypassed during normal boot.
Si retains its existing policy.

The first Hyprlock unlock after boot must use the password matching the login
keyring. The separately installed `/usr/local/lib/security/pam_oo7_tjik.so`
adds `unlock_on_auth` to oo7's PAM integration. Fedora's packaged `pam_oo7.so`
and oo7 daemon are retained. The source lives in TjikOS `apps/oo7-pam`, based
on the oo7 revision packaged by Fedora 45.

Hyprlock calls `pam_authenticate` and then `pam_end` without opening a PAM
session. In auth-only mode the module holds the password in zeroizing memory
and sends it through oo7's user-owned socket only at `pam_end(PAM_SUCCESS)`.
Authentication failure, replaced data, empty passwords and biometric-only
attempts do not send a secret. The module never stores passwords in files,
arguments or environment variables. An unavailable keyring does not override
the system authentication result.

The Hyprlock PAM stack uses `substack system-auth` so that sufficient-module
shortcuts remain within the host authentication stack and the optional keyring
module can run afterwards. The final PAM result controls delivery, including
failures from other required modules. Fingerprints can unlock an existing
session, but cannot decrypt a still-locked password-protected keyring.

`hyprlock-login.service` requests oo7 alongside the locker and uses zero grace,
immediate rendering and no fade-in. It skips the initial lock only for an
explicit `gdm-password` session; fallback password login is therefore usable
without a redundant lock. Autologin, other methods and failed logind queries
retain the initial lock. The user unit must remain enabled.

Tjikup requires `system:hyprlock-keyring` before applying system files. Its
read-only installation check verifies the source fingerprint, deployed bytes
and root ownership/mode. The normal installer builds incrementally and replaces
the module atomically. Selected configuration runs only check that dependency;
they fail rather than silently build/install a missing prerequisite. Initial
provisioning needs Rust/Cargo available before this installation step.

Validate with `bash scripts/validate.sh` in both Dotjik roots and `cargo test`
in TjikOS `apps/oo7-pam`. `python3 apps/oo7-pam/tests/daemon.py` additionally
uses Fedora's real oo7 daemon, a private D-Bus session, temporary encrypted
keyring and synthetic tokens; it requires python3-dbus and dbus-run-session.
No test uses the real account password or the live keyring. A fresh login is
still needed to verify the complete boot-to-Hyprlock flow on each host.
