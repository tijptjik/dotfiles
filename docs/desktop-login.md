# Desktop login and credential-store unlocking

Fi and Li use GDM password login. Fedora 45's packaged `gdm-password` PAM
stack invokes `pam_oo7.so` during authentication and session opening, so oo7
can unlock the keyring before desktop applications request credentials.
The keyring password must match the login password for automatic unlocking.

Hyprlock remains the screen locker for an existing session. The enabled
`hyprlock-login.service` skips its initial lock only when logind identifies
the user's display session as `gdm-password`. Autologin, other login methods,
and failed or empty logind queries retain the initial lock. This fallback
also protects a client whose home policy has arrived before its GDM policy.
Si retains its existing autologin policy.

With oo7 0.7.0 beta, adding an optional PAM authentication line to Hyprlock
does not unlock the keyring: oo7 stashes the password during authentication
and sends it to its daemon during `pam_sm_open_session`. Hyprlock only calls
`pam_authenticate` and `pam_end`. Do not claim that an auth-only hook fixes
this combination, or remove the required host authentication stack.

Validate changes with `bash scripts/validate.sh` in both the repository and
`system/` roots. The tests render Fi, Li and Si separately and mock logind;
they do not authenticate against a real account. After normal native Tjikup
deployment, a fresh client login is needed to verify GDM authentication,
keyring unlocking, and the absence of a redundant initial Hyprlock prompt.
Configuration checks alone do not establish that live acceptance result.
