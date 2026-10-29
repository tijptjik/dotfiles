# Enrolling a device

The reviewed Fedora x86_64 bootstrap installs `ca-certificates curl git fish gum
age jq rclone`, fetches pinned public Dotjik/TjikOS revisions over HTTPS, and
verifies pinned native Tjikup and Synctjik binaries by SHA-256. It does not
compile applications or run the selected maintenance graph.

1. Review the built `/init` script and its `--plan` output.
2. Run it as the normal sudo-capable user in an interactive terminal.
3. Enroll the hostname, role and explicit subscriptions with `tjikup new device`.
4. Unlock the encrypted Bitwarden token and age identity. Private files are
   `~/.config/bws/environment` and `~/.keys/age.txt`, mode 0600.
5. Tjikup validates enrollment and renders missing archive transport/policy
   natively. Existing local transport and policy are preserved.
6. Synctjik enrolls archive collections, restores required data, verifies
   readiness, and enables scheduled backups only after readiness succeeds.
7. Review `tjikup --plan`, then run `tjikup --skip-repo-sync --show-skips`.

Public source access uses HTTPS. Configure write access separately if this
device needs to push. Keep credentials, restoration captures and device-private
state out of the repositories. Repeat bootstrap only against the reviewed
revision; it refuses to reset or overwrite an unrelated checkout.

Release publication and pin changes are deferred. Existing pins do not yet
provide this migration. Incompatible binaries are rejected before replacement;
use the locally built runner for source validation until publication is approved.
