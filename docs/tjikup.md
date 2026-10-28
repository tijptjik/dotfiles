# Fleet updates with tjikup

The reusable runner lives in [tjikos/apps/tjikup](https://github.com/tijptjik/tjikos/tree/main/apps/tjikup).
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
prerequisites succeed. System pull can overlap home capture/commit; tjikOS and
home pulls can run concurrently after the capture commit. Each configuration-repository
push can start after its own pull. Both pushes and
the tjikOS update must finish successfully before apply starts. The apply stage then uses one graph
for home and system hooks, with shared resource locks and one worker limit.
Chezmoi and Chezetc retain ownership of managed files and once/onchange state.

Capture still validates every result before writing sources and commits only
changed capture targets. Fcitx capture retains its private backups. Configuration
repositories require a clean worktree after the scoped capture commit and use
`pull --rebase --no-autostash`. Dirty tracked, staged, or untracked files fail
pull/push and block apply; unknown worktree or upstream state is also an error. A whole-workflow
lock prevents overlapping Tjikup capture/pull/apply transactions in this checkout;
individual Git commands also retain their repository locks. Failed tasks stop new
work, drain running tasks, and block pending dependents. A configuration-refresh
warning prevents subsequent apply stages.

The **Fleet repositories** stage also checks tjikOS at `$TJIKOS_REPO`, or
`~/code/tjikos` by default. Clean checkouts fetch their configured upstream and
advance only by fast-forward. Dirty checkouts fail and block apply. Detached,
untracked-branch, locally ahead, or diverged checkouts produce a warning and
retain the local source for installation.
tjikOS is never automatically committed, stashed, rebased, reset, or pushed.
Fetch failures, busy checkouts, and unfinished Git operations block apply.
A missing checkout is left to the existing installer bootstrap; legacy checkout
migration rules still apply. Installers run after this stage and retain their
source-fingerprint checks.

The final home service hook refreshes changed running user services after all
home and system installers finish, before final network/release checks. It tracks
unit definitions, entry points, installed code and configuration using content
hashes in `~/.local/state/tjikup/user-services.json`. Notjik and its Telegram
bridge, Bartjik, Codex LB, Collie, Hyprvoice, Hypridle, Hyprsunset, Hyprpaper,
Hyprpolkitagent and oo7 are covered by
[`user-service-inputs.json`](../scripts/user-service-inputs.json). Changed managed
timers are rearmed without restarting their running jobs. Stopped services stay
stopped, preserving idle/nightlight choices and headless sessions. Runtjik's
installer already closes its resident launcher when its runtime changes; the
next invocation launches the new version.

The first refresh establishes the hash baseline by restarting covered active
units once. Later unchanged applies skip them. Finish replies, recordings and
Codex requests before updating: a changed service is restarted automatically.
Backup/sync jobs, lock-screen activation, recording jobs and unrelated system
daemons are outside this refresh; their existing lifecycle policies remain in
effect. Failed restarts fail the apply and keep the previous hash for retry.
The same refresh runs at the end of a direct `chezmoi apply`.

Preview or refresh selected units without running the Git/update workflow:

```sh
python3 scripts/refresh-user-services.py --check
python3 scripts/refresh-user-services.py --unit notjik.service --unit bartjik.service
```

The generated `~/.local/share/applications/mimeinfo.cache` is ignored by Chezmoi
and excluded from capture. Desktop tools regenerate it from installed desktop
entries, so Tjikup neither requires a tracked source nor captures or restores
stale associations.

## Git-only shortcuts

Available on `fi`, `li`, and `si`, from any working directory and shell:

```sh
tjix                 # push committed changes in Dotjik, Systjik, and tjikOS
tjixx                # pull all three with rebase, then push all three
tjix --dry-run       # show repositories and commands, without network or writes
tjixx --dry-run      # also check that all three working trees are clean
tjix --verbose      # include repository paths and successful Git output
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
keeps the spinner rows together. Successful Git output and repository paths are
hidden by default; `-v`/`--verbose` shows them. Failures always include Git's
diagnostics, and dirty working trees still get a short notice. Redirected output,
`TERM=dumb`, missing Gum, or `TJIKUP_NO_SPIN=1` use plain
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
`~/.local/share/chezetc`. Both Git-only shortcuts, the full `tjikup` workflow,
and app installers target tjikOS at `~/code/tjikos` (`tijptjik/tjikos`). Set
`TJIKOS_REPO` to select another checkout. The retired `TOOLTJIK_REPO` override
and existing Tooltjik directories are not selected automatically.
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

Before the hook progress display starts, `Chezmoi files` and `Home hooks` each
show an immediate status and a completion time. Interactive runs also print
elapsed time every five seconds during these phases. These append-only updates
avoid clearing Chezmoi diagnostics or prompts. Redirected logs retain the start
and completion rows; `TJIKUP_PROGRESS=0` disables periodic updates. Preparation
rows do not add duplicate stages to the final outcome report.

The combined home/system graph defaults to four workers (`FLEET_JOBS=1` serializes
it for diagnosis). Cargo, uv, tjikOS checkout/install operations, DNF, Flatpak,
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
order crosses application sections. Si’s application update results retain
separate `Docker services` and `Native applications` headings, with an individual
icon and outcome for each service. Direct `chezmoi apply` and `chezetc apply`
keep their native serial sequences and headings.

Completed rows use the hooks' reported outcomes instead of the manifest's
planned action. Explicit unchanged results are `SKIP`; a later skipped substep
does not hide an earlier change. Multiple different actions are summarized as
`APPLY`. Hooks removed by a host condition render to only the standard deferral guard;
these are silent skipped dependency nodes and are never executed. Other hooks
that emit no status finish as `DONE`, which confirms completion without claiming
a configuration change. Warnings and failures retain their
diagnostics. Cached installers pass their unchanged result through the wrapper.

Actions and icons share outcome colours: green for success, grey for skips,
yellow for warnings, red for failures, and cyan while running. Service names are
white; parenthesized subtypes and right-hand notes are dim. Pure asset tasks use
`Assets` as the service, for example `Assets (fonts)` and `Assets (Rose Punk icons)`.
Kitty 0.40+ uses 32px colour icons in two-line rows, with normal-size text
vertically centred beside them. Images use the Rose Punk theme where available
and matching glyph tiles otherwise. They travel inline through the runner and
SSH; Unicode placeholders make scrolling and progress redraws erase/move the
images with their rows. Terminal cell dimensions keep the artwork at 32px.
Image data is bundled in `scripts/fleet_update/icons32.json`, so the update
does not need an image converter. To rebuild it after changing artwork, run
`python3 scripts/icons/build-fleet.py` (requires Pillow and ImageMagick).

Colour image rows leave one terminal cell between the checkmark and icon canvas,
and the same gap between the canvas and label. Chrome, Sublime Text and Obsidian
use their Rose Punk application artwork. Icon cache and Rose Punk icon rows use
the four-tile icon-grid artwork, and
Greetjik uses its named application artwork.

Herdr 0.9.5+ also uses 32px colour icons and two-line rows. Its panes advertise
`TERM_PROGRAM=herdr` and `HERDR_ENV=1`, with `TERM=xterm-256color`. Because its
PTY ioctl omits pixels, Tjikup asks Herdr for cell dimensions once at renderer
startup (a bounded `CSI 16 t` query, skipped if input is already pending).
Herdr does not render Kitty's OSC 66 text sizing, so this path uses normal
text beside the top-aligned icon instead of the centred-text protocol.
Keep `[terminal] kitty_graphics = true` in Herdr's configuration. The 0.9.5
path is verified locally; remote sessions also need the updated fleet scripts.

Other terminals, tmux/screen sessions, and terminals without usable pixel geometry
keep compact Nerd Font icons. Set `TJIKUP_KITTY_ICONS=0` to select this compact
layout in Kitty, or `TJIKUP_ICONS=0` to disable all title icons. Running and
completed rows use the same icons; outcome marks remain separate. Reports and
redirected plain output retain text labels. `TJIKUP_ICONS=1` forces glyphs into
a plain captured preview; it does not send image data to ordinary log output.

Each combined apply links its private report as a compact `REPORT ↗ Task timings`
row, with the run ID at the right. The link carries the originating hostname so
Kitty can open remote reports through its remote-file handler. Ordinary redirected
logs and dumb terminals retain the full `Task timings: /path/to/timings.json` line.
Reports live under
`$XDG_STATE_HOME/tjikup/logs/apply-*` (default `~/.local/state/tjikup/logs`). The report
records total apply time, home file/rendering time, task dependencies/resources,
execution duration, dependency wait,
resource/terminal wait, worker wait and start/finish offsets. System native file
application and rendering are recorded together as a task. Hook output lives
alongside it in private log files, including interactive hooks. Those hooks stream
prompts and diagnostics while structured status rows appear once in the scheduler.
Failure reports retain completed/failed/blocked task timing; cancellation preserves the
completed events and marks unfinished tasks interrupted. These measurements do
not imply a live speedup until representative runs have been compared.

Routine `tjikup` installs missing Cargo tools and Codex LB without asking package
registries for newer versions. Use `tjikup --upgrade` to retain those home package
upgrade checks. Direct `chezmoi apply` retains the previous upgrade behavior.
Python still uses `uv sync` to converge the declared environment and reports
failures correctly. Font and icon tools use their native freshness checks instead
of forced rebuilds.

Herdr binary updates are manual on Fi, Li and Si. Neither `tjikup` (including
`--upgrade`) nor direct `chezmoi apply` updates an existing binary. Run
`herdr update` outside Herdr when ready to update, closing active sessions if
requested. The once-only install hook still installs a missing binary, and
recurring hooks continue provisioning Herdr plugins.

Tjikup, Notjik and Greetjik build/install steps compare source fingerprints against
all declared installed outputs, including bytes, modes and symlink targets.
Changed inputs, changed/deleted outputs, or a missing record trigger installation.
Only successful installs with stable inputs create an atomic record under
`$XDG_STATE_HOME/tjikup/install` (default `~/.local/state/tjikup/install`).
Service/migration checks remain outside the build cache. The cache is local and
does not stand in for checking runtime service state. Removing a record forces
that install to run again. Build directories and dependency caches are excluded
from source fingerprints. New installer inputs/outputs must be added to its
`cache-install.py` invocation.

The **Fleet repositories** panel keeps three rows in fixed order: `dotjik`,
`systjik`, `tjikOS`, each with separate `PULL` and `PUSH` cells. Pending cells
are dimmed, running cells are bright, completed operations with changes are
blue, and completed operations without changes are teal. Failures turn red;
blocked operations stay dimmed. tjikOS PUSH remains dimmed because this workflow
does not publish its development commits. Pull changes are determined from the
checkout's HEAD before and after the operation, and pushes from outgoing commits.
The scoped capture commit stays under **Commit Local Changes**; dirty checks are
folded into repository results. Redirected output emits the three final rows
with explicit state names and no cursor controls.
Dirty checkout failures retain their concrete reason in the final Issues list.
Blocked apply does not insert a separate step row into the repository panel.
With the updated runner, reported repository failures do not add generic
`Fleet update` and `Tjikup` failures; the command still exits nonzero.

The fleet panel uses the tjikOS runner's synchronized terminal frames and cursor
handling. Hook progress continues to show a live row per task with a spinner and
elapsed time. The cursor returns for prompts and when the progress context exits,
including Ctrl-C. Fleet panel changes take effect directly from this checkout;
changes to the reusable runner require reinstalling tjikOS.
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
`--dry-run` executes prerequisite checks, capture previews, and read-only tjikOS
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

The managed installation hook and focused installer use `~/code/tjikos` on
every host, unless `$TJIKOS_REPO` explicitly selects another checkout. If absent
they clone tjikOS there using `git@github.com:tijptjik/tjikos.git` (SSH), so
later pushes use the host's GitHub SSH key. Existing remotes are preserved;
changing the clone URL does not migrate earlier HTTPS checkouts. On an affected
host, stop any running Git sync and update the existing origin:

```sh
git -C ~/code/tjikos remote set-url origin git@github.com:tijptjik/tjikos.git
git -C ~/code/tjikos remote -v
```

If an explicit `remote.origin.pushurl` still uses HTTPS, update it with
`git remote set-url --push` in that checkout too. `git://` is not SSH and cannot
provide authenticated GitHub pushes.

Existing checkouts are never pulled by installers;
the fleet repository stage updates clean checkouts before installation. For a
standalone installation, update tjikOS explicitly first. The installer builds
and installs only tjikup. For a checkout that can fast-forward:

```sh
git -C ~/code/tjikos fetch origin
git -C ~/code/tjikos merge --ff-only origin/main
TJIKOS_REPO=~/code/tjikos bash ~/.local/share/chezmoi/scripts/install-tjikup.sh
```

If startup reports `No module named 'tjikup.progress'` or says the runner is
outdated, the fleet workflow requires a newer runner than the installed copy.
Run the tjikOS update and focused installer commands above on the affected
host, then run `tjikup --dry-run` before retrying `tjikup`. Use your
`TJIKOS_REPO` path instead if you selected a different checkout. The runner
passes its own bundled Python modules to fleet subprocesses, so updating the
tjikOS source alone is insufficient: reinstall the executable too.
`tjikup --check` only checks configuration syntax and cannot detect this mismatch.
The focused installer checks the source dependency before replacing the runner,
then checks the installed bundle before linking the configuration.

Existing Tooltjik checkouts can remain in place while tjikOS is cloned into
`~/code/tjikos`. Preserve their local work separately; installers do not rename
those directories or rewrite their remotes. Replace any `TOOLTJIK_REPO` setting
with `TJIKOS_REPO` pointing to the intended tjikOS checkout.

If tjikOS was previously cloned to `~/.local/share/tjikos` and
`~/code/tjikos` does not exist, installers and the fleet update stage stop with migration
guidance rather than creating a second clone. Move the existing checkout while
no tjikOS build or Git operation is running; this preserves commits, staged
changes and untracked files. In Bash, when the destination is absent:

```bash
mkdir -p "$HOME/code"
if [[ ! -e "$HOME/code/tjikos" && ! -L "$HOME/code/tjikos" ]]; then
    mv -T -- "$HOME/.local/share/tjikos" "$HOME/code/tjikos" &&
        ln -s -- "$HOME/code/tjikos" "$HOME/.local/share/tjikos"
fi
```

The compatibility symlink keeps existing service paths valid. If both checkouts
already exist, reconcile their histories and local changes before removing
either. Linked Git worktrees require `git worktree move` instead of `mv`.

The installer fails clearly if the checkout does not yet contain tjikup.
The command and notification icon belong to tjikOS;
Chezmoi no longer installs runner code into `~/.local/lib/tjikup`. An old copy
there is unused by the new self-contained executable and may be removed after
migration. No blanket apply is needed to migrate the command.

Setup hooks use Charmbracelet’s `gum spin` with elapsed time on terminals,
including during a plain `chezmoi apply`. tjikOS downloads also show Git’s progress percentage,
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
TJIKOS_REPO=~/code/tjikos bash scripts/validate.sh
```

The fleet declares `--skip-conflicts`; it is not hard-coded in the runner.
Dry-run never commits, pulls, pushes, applies, or writes capture backups.
`--check` validates configuration structure without invoking any commands.
A different source checkout is selected through `--config`; legacy
`TJIKUP_REPO`/`TJIKUPDATE_REPO` overrides are replaced by that explicit interface.
Use `TJIKUP_CONFIG` for a persistent configuration override.

Tests import the external runner using `TJIKOS_REPO`, a sibling checkout,
`~/code/tjikos`, or a caller-supplied `PYTHONPATH` (which can point at the
installed zipapp). Fleet tests use isolated homes, repositories and mocked
commands. They do not validate real package updates or services on fi/li/si.
See [completion notifications](tjikup-notifications.md) for desktop behavior.

The client home apply also [installs Bartjik and retires Waybar](bartjik.md),
including enabling its user service and starting it in an active desktop session.

## Runtjik-only installation

`runtjik` is included in the home hook graph on every host. Its installer verifies
both tjikOS source and deployed file fingerprints, rebuilding changed or stale
installations and preserving `~/.config/runtjik/runtjik.conf`. The headless server
receives the files and CLI without a GUI service.

Use `tjikup --config scripts/runtjik-install.json` from the Dotjik checkout for
a focused app-only installation. It uses the existing tjikOS source and avoids
repository capture/commit/sync; this is useful while unrelated work is dirty. It
does not publish new app code or bypass the normal full-workflow clean-worktree
requirements. See [launcher tools](launcher-tools.md) for migration details.
