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
prerequisites succeed. System pull can overlap home capture/commit; Tooltjik and
home pulls can run concurrently after the capture commit. Each configuration-repository
push can start after its own pull. Both pushes and
the Tooltjik update must finish successfully before apply starts. The apply stage then uses one graph
for home and system hooks, with shared resource locks and one worker limit.
Chezmoi and Chezetc retain ownership of managed files and once/onchange state.

Capture still validates every result before writing sources and commits only
changed capture targets. Fcitx capture retains its private backups. Configuration
repositories use `pull --rebase --autostash`; unknown upstream state is an error. A whole-workflow
lock prevents overlapping Tjikup capture/pull/apply transactions in this checkout;
individual Git commands also retain their repository locks. Failed tasks stop new
work, drain running tasks, and block pending dependents. A configuration-refresh
warning prevents subsequent apply stages.

The **Fleet repositories** stage also checks Tooltjik at `$TOOLTJIK_REPO`, or
`~/code/tooltjik` by default. Clean checkouts fetch their configured upstream and
advance only by fast-forward. Dirty, detached, untracked-branch, locally ahead,
or diverged checkouts produce a warning and retain the local source for installation.
Tooltjik is never automatically committed, stashed, rebased, reset, or pushed.
Fetch failures, busy checkouts, and unfinished Git operations block apply.
A missing checkout is left to the existing installer bootstrap; legacy checkout
migration rules still apply. Installers run after this stage and retain their
source-fingerprint checks.

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
pulls all three concurrently before pushing all three concurrently. Every pull
must succeed before any push starts. If a stage fails, it waits for its running
peers, reports the failures, and skips subsequent stages. A conflict
is left available for normal Git resolution. Earlier successful pulls or pushes
are not rolled back; the operation is not atomic across repositories. No force
push is used. Each branch must have an upstream.

On terminals, Charmbracelet Gum animates a row for each repository with `PULL`
or `PUSH`, elapsed seconds, and `OK`/`FAILED` completion status. A shared renderer
keeps the spinner rows together and prints Git output by repository after each
stage. Redirected output, `TERM=dumb`, missing Gum, or `TJIKUP_NO_SPIN=1` use plain
status lines. `--dry-run` describes the parallel stages without launching Gum or
running network operations. Rebase continuation remains sequential before these
stages.

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
`~/.local/share/chezetc`. Tooltjik uses `TOOLTJIK_REPO` when set, otherwise
`~/code/tooltjik` on every host, matching installer selection.
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

The combined home/system graph defaults to four workers (`FLEET_JOBS=1` serializes
it for diagnosis). Cargo, uv, Tooltjik checkout/install operations, DNF, Flatpak,
user/system systemd, Tailscale, fonts and storage have shared resource exclusions.
Native file passes and wrapper setup own the terminal. llmtrim's package install
is separate from setup; setup only owns the terminal when its CA is missing.
Worker hooks must be noninteractive, and system workers require noninteractive
sudo. The managed passwordless-sudo bootstrap remains Chezmoi's responsibility.

System file application can begin after home files and the Chezetc wrapper are
ready. It no longer waits for all home hooks. Chezetc retains its native
configuration-refresh retry and before/once/onchange handling, while audited
maintenance hooks are deferred to the shared graph. The system inventory lives
in Chezetc's `scripts/tjikup-plan.json`; unknown, missing or undeferable hooks fail
closed. System hooks are rendered through the wrapper in the correct template
context and syntax-checked before any deferred system hook starts. Do not set
`FLEET_DEFER_SYSTEM_HOOKS` manually.

RPM maintenance follows repository setup. Flatpak maintenance waits for RPM
packages so its executable is available on first apply; independent application
installers and home hooks may overlap. Hooks that can install packages retain a
DNF resource lock for their whole execution. Existing package transactions and
upgrade policy, Plex exclusions and Nginx rebuild ordering remain intact. The
Tailscale reconciliation waits for home/system work before enforcing the declared
final network policy. Fedora release-upgrade prompting is exclusive and runs last,
after every peer task, so a reboot cannot interrupt in-flight work.

Both layers share one `Home and system configuration` heading because completion
order crosses application sections. Direct `chezmoi apply` and `chezetc apply`
keep their native serial sequences and headings.

Each combined apply prints a private `timings.json` path under
`$XDG_STATE_HOME/tjikup/logs/apply-*` (default `~/.local/state/tjikup/logs`). The report
records total apply time, home file/rendering time, task dependencies/resources,
execution duration, dependency wait,
resource/terminal wait, worker wait and start/finish offsets. System native file
application and rendering are recorded together as a task. Hook output lives alongside it in private log files. Failure
reports retain completed/failed/blocked task timing; cancellation preserves the
completed events and marks unfinished tasks interrupted. These measurements do
not imply a live speedup until representative runs have been compared.

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
result each; their raw output is saved in private `apply-*` directories under the
same log root. Warnings and failure diagnostics remain visible. Successful tool
chatter and duplicate `DAG` rows are hidden. Interactive hooks own the terminal
exclusively.

The Python package count uses quiet output. Python 3.13 remains pinned for
PaddlePaddle: release 3.3.1 has CPython 3.13 wheels but no CPython 3.14 wheels.
`--dry-run` executes prerequisite checks, capture previews, and read-only Tooltjik
inspection, without fetching, changing Git history, applying, installing, or writing
caches. `tjikup --check` validates the outer runner JSON;
the DAG and complete hook inventory are validated when the workflow starts.
Regression tests cover overlap, resource exclusion, failure propagation, skip
invalidation, dry-run behavior, and template rendering for fi/li/si. These checks
do not constitute a live system apply or a measured production speedup.

## Installation and migration

For a clean Fedora device, start with the [initialization instructions](../README.md#installation-on-new-machine).
Initialize both configuration repositories and the Chezetc wrapper before using
the fleet workflow. The normal home apply hook installs the runner automatically.

For an existing device, update the dotfiles and Chezetc checkouts to compatible
revisions, including Chezetc's `scripts/tjikup-plan.py` adapter and hook manifest,
then run the focused installer as the normal user:

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

The managed installation hook and focused installer use `~/code/tooltjik` on
every host, unless `$TOOLTJIK_REPO` explicitly selects another checkout. If absent
they clone Tooltjik there. Existing checkouts are never pulled by installers;
the fleet repository stage updates clean checkouts before installation. For a
standalone installation, update Tooltjik explicitly first. The installer builds
and installs only tjikup. For a checkout that can fast-forward:

```sh
git -C ~/code/tooltjik fetch origin
git -C ~/code/tooltjik merge --ff-only origin/main
TOOLTJIK_REPO=~/code/tooltjik bash ~/.local/share/chezmoi/scripts/install-tjikup.sh
```

If startup reports `No module named 'tjikup.progress'` or says the runner is
outdated, the fleet workflow requires a newer runner than the installed copy.
Run the Tooltjik update and focused installer commands above on the affected
host, then run `tjikup --dry-run` before retrying `tjikup`. Use your
`TOOLTJIK_REPO` path instead if you selected a different checkout. The runner
passes its own bundled Python modules to fleet subprocesses, so updating the
Tooltjik source alone is insufficient: reinstall the executable too.
`tjikup --check` only checks configuration syntax and cannot detect this mismatch.
The focused installer checks the source dependency before replacing the runner,
then checks the installed bundle before linking the configuration.

Older installations may still have `~/.local/share/tooltjik`. If it exists and
`~/code/tooltjik` does not, installers and fleet Git commands stop with migration
guidance rather than creating a second clone. Move the existing checkout while
no Tooltjik build or Git operation is running; this preserves commits, staged
changes and untracked files. In Bash, when the destination is absent:

```bash
mkdir -p "$HOME/code"
if [[ ! -e "$HOME/code/tooltjik" && ! -L "$HOME/code/tooltjik" ]]; then
    mv -T -- "$HOME/.local/share/tooltjik" "$HOME/code/tooltjik" &&
        ln -s -- "$HOME/code/tooltjik" "$HOME/.local/share/tooltjik"
fi
```

The compatibility symlink keeps existing service paths valid. If both checkouts
already exist, reconcile their histories and local changes before removing
either. Linked Git worktrees require `git worktree move` instead of `mv`.

The installer fails clearly if the checkout does not yet contain tjikup.
The command and notification icon are tooltjik-owned;
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
