# Fi native file candidate

This manifest is a parallel migration candidate for Tjikup's native file engine.
It is **not included in the active fleet recipe graph**. Chezetc's sources and Go
templates remain intact and authoritative; home templates are unaffected.

The candidate covers Fi's 18 declared targets: 14 regular files, 2 symlinks, and
2 absent targets. It uses MiniJinja for the existing system templates. Static
source files are copied here so this candidate can be evaluated independently.
When editing these files during evaluation, retain rendering parity with `etc/`.
The manifest is guarded to host `fi` and represents Fedora 45's current selection.
Li and Si are not migrated by this candidate.

The existing `/etc/usr/local/bin/bun -> /home/root/.bun/bin/bun` link is deliberately
preserved for comparison. Its incorrect placement/target needs a separate reviewed
cleanup before adopting a corrected native configuration. Template identity must
come from explicit context, not sudo's effective username.

From the Systjik repository, verify using the candidate Tjikup binary:

```sh
sudo -n python3 -B scripts/check-native-fi.py \
  --tjikup /home/io/code/tjikos/apps/tjikup/target/release/tjikup \
  --manifest native/fi/manifest.json \
  --legacy-config /home/io/.config/chezmoi/chezetc/chezmoi.toml \
  --output /tmp/tjikup-native-fi-verification
```

The output directory must not exist. The script applies into that isolated root,
compares every target with Chezetc, validates ownership/modes, applies again and
checks that file and state inodes/timestamps remain unchanged. It also runs a
read-only native plan against live `/`, verifies that no live targets changed,
and writes `verification.json`. No package hooks, services or archive workers run.
Exit 0 from the live plan proves equality; a conflict or difference is recorded
in the report and must be resolved before switching ownership of the targets.

To eventually activate native deployment, replace the `system:files` action for
Fi with native `files check/apply` commands, using one root-owned state directory
such as `/var/lib/tjikup/files`. Do not enable both managers for the same paths.
This activation and removal of Chezetc are intentionally outside this candidate.
