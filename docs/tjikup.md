# Tjikup fleet workflows

Tjikup is the native Rust runner in TjikOS. Dotjik owns declarative policy in
this repository. Synctjik owns backups, restoration, replication, readiness and
backup scheduling. Fleet orchestration and help do not require Python. Python
applications and development/test utilities retain their own runtimes.

## Public commands

- `tjikup --plan` validates and displays the selected recipe graph.
- `tjikup` captures declared live settings, synchronizes the two repositories,
  deploys configuration, and runs selected installation/maintenance recipes.
- `tjikup --skip-repo-sync` runs local policy without repository synchronization.
- `tjikup --apply-dotfiles` and `--apply-sysfiles` select configuration workflows.
- `dotjik [plan|diff|check|apply]` delegates to `tjikup config home`.
- `systjik [plan|diff|check|apply]` delegates to `tjikup config system`.
- `dotjik edit TARGET` locates the declared native source and opens your editor.
  `source-path [TARGET]` prints its location. Declare new ownership explicitly
  in the manifest; there is no automatic add command.
- `tjix` delegates to `tjikup git push`: push existing commits only.
- `tjixx` delegates to `tjikup git sync`: pull every repository with rebase,
  then push only after all pulls and preflights succeed.
- `fleet-ssh HOST` delegates to `tjikup ssh HOST`, using pinned fleet identity.

Git-only shortcuts never stage, commit, stash, reset or force-push. Sync requires
clean trees. A resolved paused rebase continues with its original message.
`--dry-run` performs local preflight only. Both shortcuts share the workflow and
repository locks with the full workflow. An SSH command is executed once even
if it fails; discovery must not replay remote work.

## Native file ownership

`native/home/files.json` owns ordinary home files from `native/home/files/`.
Credential manifests use private templates in `native/home/templates/`.
`system/native/{fi,li,si}/manifest.json` owns system files. MiniJinja `.j2`
templates can produce configuration files or scripts. The preparation rows are
**Templates (home)** and **Templates (system)**. Maintenance batches live in
`native/tasks/`; shared shell helpers live in `native/helpers/`.

File applies preserve drift, use private recovery receipts and do not run
maintenance tasks implicitly. System file deployment installs the current
native maintenance binary at `/usr/local/lib/tjikup/tjikup`. Plan and check
never install it. `tjikup system --help` lists system operations; policy lives
in `/etc/tjikup/maintenance.json` and enforces the target hostname and privilege.

Credentials use `~/.keys/age.txt`. Existing identities are copied once from the
previous private filename by an explicit apply; the original remains intact.
Read-only plans can read the previous identity without creating files.

## Installation and maintenance

`native/installers.json` declares release identity, artifacts, checks and target
paths. `tjikup workflow install NAME` verifies release digests and deployed
bytes, preserves newer installed releases, and rejects unmanaged executables.
`workflow bitwarden` owns bws/bw bootstrap. `workflow desktop` owns launcher
preservation, duplicate-launcher cleanup and icon override migration.

`workflow repositories`, `capture`, `services`, `cache-install`, `package`,
`timing` and `progress` are native helpers. Use `tjikup workflow --help` for their
interfaces. Policy scripts contain only application-specific shell steps.
`native/fleet.json` declares host identities and discovery; the public command
never changes known-host trust based on discovery results.

Si storage/provisioning, NSS, permissions, media guard, Transmission cleanup and
application updates run through `tjikup system`. Updates share backup locks and
require a fresh backup. Storage mutations require verified mount identities.
Permission changes preserve owners/content/mtime and journal metadata first.
Use the server recovery guides before applying policy to a rebuilt server.

## Validation and release status

`bash scripts/validate.sh` runs policy regression tests and renders maintenance
templates for Fi, Li and Si without executing them. Set `TJIKUP_BINARY` to the
binary under test. Native behavior tests live in TjikOS `apps/tjikup/tests` and
Rust module tests; fixtures never require live credentials or services.

Release publication and bootstrap pin updates are deferred. Source completion
does not make the existing published bootstrap contain these commands. The
bootstrap verifies required capabilities before replacing an installed runner.
