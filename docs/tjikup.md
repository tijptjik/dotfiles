# Fleet updates with tjikup

The reusable runner lives in [tooltjik/apps/tjikup](https://github.com/tijptjik/tooltjik/tree/main/apps/tjikup).
This repository owns [tjikup.json](../tjikup.json), the order of fleet operations,
and [scripts/fleet_update](../scripts/fleet_update), which captures our live
application settings and applies home configuration. Chezetc owns
`scripts/tjikup-apply.py`, including system configuration refresh and retry.
The runner has no built-in Chezmoi, Chezetc, Git, host or credential policy.
The workflow also declares repository banners and section headings. Capture,
prerequisite and commit scripts own their detailed rows, so their steps disable
the runner's duplicate summary rows.

The fleet uses a bounded DAG scheduler in `scripts/fleet_update/dag.py`.
[workflow.json](../scripts/fleet_update/workflow.json) declares repository and apply
dependencies; [home-plan.json](../scripts/fleet_update/home-plan.json) declares home
hook dependencies and shared resources. Ready tasks start as soon as their
prerequisites succeed. System pull can overlap home capture/commit; each push
can start after its own pull. Both pushes must succeed before apply starts.

Capture still validates every result before writing sources and commits only
changed capture targets. Fcitx capture retains its private backups. Git uses
`pull --rebase --autostash`; unknown upstream state is an error. A whole-workflow
lock prevents overlapping Tjikup capture/pull/apply transactions in this checkout;
individual Git commands also retain their repository locks. Failed tasks stop new
work, drain running tasks, and block pending dependents. A configuration-refresh
warning prevents subsequent apply stages.

Capture also copies the live `~/.local/share/applications/mimeinfo.cache` into
its tracked source before apply. Desktop tools regenerate this file, so the live
associations take precedence, including removed entries. The normal scoped capture
commit includes these updates automatically. Missing caches are skipped, and
`--dry-run` only previews changes. Plain `chezmoi apply` does not run this capture;
use `tjikup` for automatic updates.

## Git-only shortcuts

Available on `fi`, `li`, and `si`, from any working directory and shell:

```sh
tjix                 # push committed changes in Dotjik, Systjik, and Tooltjik
tjixx                # pull all three with rebase, then push all three
tjix --dry-run       # show repositories and commands, without network or writes
tjixx --dry-run      # also check that all three working trees are clean
dotjik diff          # compatibility wrapper for chezmoi
systjik diff         # compatibility wrapper for chezetc
```

Dotjik is the personal configuration name; Systjik is the system configuration
name. The system GitHub repository is `tijptjik/systjik`; the personal repository remains
`tijptjik/dotfiles`. The upstream tools (`chezmoi`, `chezetc`), existing aliases,
and checkout paths remain unchanged. These wrappers
forward arguments and exit status directly to the original tools.

The shortcuts synchronize this host's three checkouts. They do not commit new work,
capture live settings, apply configuration, install tools, or contact other fleet
hosts. `tjikup` remains the full update workflow. Push-only `tjix` permits dirty
files but sends only committed history. `tjixx` requires all three working trees
(including untracked files) to be clean; commit or stash intentionally beforehand.
It explicitly uses `git pull --rebase --no-autostash`, so it never temporarily
hides ongoing work. It checks every repository before any network operation,
pulls all three before pushing any, and stops on the first failure. A conflict
is left available for normal Git resolution. Earlier successful pulls or pushes
are not rolled back; the operation is not atomic across repositories. No force
push is used. Each branch must have an upstream.

Both shortcuts detect an existing rebase before checking the branch, since a
rebase temporarily detaches HEAD. After checking all three repositories, they run
`git rebase --continue` with the existing commit message. Resolve conflicts and
stage the intended resolutions with `git add` first; the shortcuts never stage,
skip, abort, or amend automatically. A clean pause at an edit step can also
continue. Unresolved conflicts or unstaged edits stop the command with guidance.
If continuation hits another conflict or pause, no repositories are pushed;
inspect the rebase, finish the next resolution and rerun. `--dry-run` only reports
the planned continuation. Other unfinished Git operations still require manual
completion. Ordinary detached HEAD checkouts are not pushed.

Dotjik is located via `chezmoi source-path` and its Git root; Systjik defaults to
`~/.local/share/chezetc`. Tooltjik uses `TOOLTJIK_REPO`, then an existing
`~/code/tooltjik`, then `~/.local/share/tooltjik`, matching installer selection.
`DOTJIK_REPO` and `SYSTJIK_REPO` override the other repository paths. Missing
checkouts fail clearly rather than being cloned. The shortcuts share Tjikup's
workflow and repository locks and report a busy checkout instead of racing it.
Git settings are passed per invocation; no global Git configuration is changed.

To install only the commands, without running provisioning hooks:

```sh
chezmoi apply --include=files ~/.local/bin/tjix ~/.local/bin/tjixx \
  ~/.local/bin/dotjik ~/.local/bin/systjik ~/.local/lib/tjik_git.py
```

## Parallel apply and skip policy

Tjikup lets Chezmoi perform its native bootstrap, before/once/onchange hooks and
file convergence, while deferring the listed `run_after_*` hooks. It then renders
and syntax-checks all deferred hooks before running their DAG. Rendering failure
blocks all deferred work. Adding or removing an after-hook requires updating the
manifest; a mismatch fails before home apply. Plain `chezmoi apply` retains its
native serial hook behavior. Never set `FLEET_DEFER_HOOKS` manually: it is an
internal hand-off flag, not a way to skip setup.

Home work defaults to four workers (`FLEET_JOBS=1` serializes it for diagnosis).
Cargo, tooltjik checkout/install operations, DNF, user-systemd, Tailscale, fonts,
and storage have resource exclusions. Herdr setup and wrapper setup run alone
with terminal access. All other parallel hooks must be noninteractive; a command
that requires credentials must have them available before dispatch. Home must
finish before Chezetc starts: home installs/configures its wrapper and runner,
and both layers can change packages, services and networking. Chezetc remains
an exclusive node with its existing provisioning order and refresh/retry policy.
Its system package/release update policy has **not** changed.

Routine `tjikup` installs missing Cargo tools and Codex LB without asking package
registries for newer versions. Use `tjikup --upgrade` to retain those home package
upgrade checks. Direct `chezmoi apply` retains the previous upgrade behavior.
Python still uses `uv sync` to converge the declared environment and reports
failures correctly. Font and icon tools use their native freshness checks instead
of forced rebuilds.

Tjikup, Notjik and Pony build/install steps compare source fingerprints against
all declared installed outputs, including bytes, modes and symlink targets.
Changed inputs, changed/deleted outputs, or a missing record trigger installation.
Only successful installs with stable inputs create an atomic record under
`$XDG_STATE_HOME/tjikup/install` (default `~/.local/state/tjikup/install`).
Service/migration checks remain outside the build cache. The cache is local and
does not stand in for checking runtime service state. Removing a record forces
that install to run again. Build directories and dependency caches are excluded
from source fingerprints. New installer inputs/outputs must be added to its
`cache-install.py` invocation.

Fleet steps use their configured verbs and labels (for example, `PULL ✓ Dotjik`)
with elapsed wall time. Steps that already print their own status do not add a
duplicate scheduler row; unchanged pushes are marked skipped. Parallel output
has one live row per task, with a spinner and elapsed time until completion.
Redirected output contains final rows without cursor controls.
Buffered failures show the failed step first, followed by
a short diagnostic and the path to a private full-output log under
`$XDG_STATE_HOME/tjikup/logs` (default `~/.local/state/tjikup/logs`). Git conflicts
include the conflict details and an inspection command; a paused rebase also
shows how to continue after resolving and staging the files. This presentation
does not resolve conflicts or resume a rebase automatically. If saving the log
fails, the complete output is printed instead. Deferred hooks leave one concise
result each; their raw output is saved in private `home-*` directories under the
same log root. Warnings and failure diagnostics remain visible. Successful tool
chatter and duplicate `DAG` rows are hidden. Interactive hooks own the terminal
exclusively.

The Python package count uses quiet output. Python 3.13 remains pinned for
PaddlePaddle: release 3.3.1 has CPython 3.13 wheels but no CPython 3.14 wheels.
`--dry-run` executes only prerequisite checks and capture previews, without Git,
apply, installs or cache writes. `tjikup --check` validates the outer runner JSON;
the DAG and complete hook inventory are validated when the workflow starts.
Regression tests cover overlap, resource exclusion, failure propagation, skip
invalidation, dry-run behavior, and template rendering for fi/li/si. These checks
do not constitute a live system apply or a measured production speedup.

## Installation and migration

For a clean Fedora device, start with the [initialization instructions](../README.md#installation-on-new-machine).
Initialize both configuration repositories and the Chezetc wrapper before using
the fleet workflow. The normal home apply hook installs the runner automatically.

For an existing device, update the dotfiles and Chezetc checkouts to compatible
revisions, then run the focused installer as the normal user:

```sh
git -C ~/.local/share/chezmoi pull --ff-only
git -C ~/.local/share/chezetc pull --ff-only
bash ~/.local/share/chezmoi/scripts/install-tjikup.sh
~/.local/bin/tjikup --check
```

`~/.config/tjikup/config.json` links to the workflow in the dotfiles source.
Chezmoi and the installer use the same normalized link target to avoid spurious
"changed since chezmoi last wrote it" conflicts. Keep this as a managed symlink;
edit `tjikup.json` in the repository instead of re-adding the live config.
Changing the workflow changes the next invocation. A run loads the configuration
once, before any scripts execute. Pulls may update subsequent scripts, matching
the existing fleet update behavior.

The installer does not commit, push, capture settings or apply either
configuration repo. It checks the system adapter exists, installs the executable
and icon, validates the workflow, and atomically links the default configuration.
It can also be run before the first home apply once Chezetc is initialized.

The managed installation hook and focused installer select `$TOOLTJIK_REPO`, an existing
`~/code/tooltjik`, or `~/.local/share/tooltjik`. If absent they clone tooltjik.
If the default `~/.local/share/tooltjik` lacks the required app, the shared
bootstrap helper updates it with `git pull --ff-only`, requiring a clean checkout.
The installer builds and installs only tjikup. Explicit selections and development
checkouts are not pulled; update tooltjik explicitly to deploy a new runner
version, for example:

```sh
git -C ~/code/tooltjik pull --ff-only
TOOLTJIK_REPO=~/code/tooltjik bash ~/.local/share/chezmoi/scripts/install-tjikup.sh
```

Use `~/.local/share/tooltjik` instead on devices with the default cloned checkout. It fails clearly if the checkout does
not yet contain tjikup. The command and notification icon are tooltjik-owned;
Chezmoi no longer installs runner code into `~/.local/lib/tjikup`. An old copy
there is unused by the new self-contained executable and may be removed after
migration. No blanket apply is needed to migrate the command.

Setup hooks use Charmbracelet’s `gum spin` with elapsed time on terminals,
including during a plain `chezmoi apply`. Tooltjik downloads also show Git’s progress percentage,
received bytes, and transfer rate. The percentage counts Git objects, not bytes:
Git does not announce the final download size in advance. Gum runs in a private
pseudo-terminal; its capability queries are answered there, and only display output reaches your terminal. It cannot consume prompt
input or leak capability replies into the shell. Redirected logs use plain status
rows; `TJIKUP_NO_SPIN=1` disables animation.

## Use and validation

```sh
tjikup                         # converge; skip installed home package upgrades
tjikup --upgrade               # also check home package registries for upgrades
tjikup --dry-run               # checks and capture preview only
tjikup --skip-conflicts        # preserve conflicting home/system files
tjikup --config ./tjikup.json --check
TOOLTJIK_REPO=~/code/tooltjik bash scripts/validate.sh
```

The fleet declares `--skip-conflicts`; it is not hard-coded in the runner.
Dry-run never commits, pulls, pushes, applies, or writes capture backups.
`--check` validates configuration structure without invoking any commands.
A different source checkout is selected through `--config`; legacy
`TJIKUP_REPO`/`TJIKUPDATE_REPO` overrides are replaced by that explicit interface.
Use `TJIKUP_CONFIG` for a persistent configuration override.

Tests import the external runner using `TOOLTJIK_REPO`, a sibling checkout,
`~/code/tooltjik`, or a caller-supplied `PYTHONPATH` (which can point at the
installed zipapp). Fleet tests use isolated homes, repositories and mocked
commands. They do not validate real package updates or services on fi/li/si.
See [completion notifications](tjikup-notifications.md) for desktop behavior.

The client home apply also [installs Bartjik and retires Waybar](bartjik.md),
including enabling its user service and starting it in an active desktop session.
