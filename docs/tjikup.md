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

The workflow checks prerequisites, captures live settings, commits only changed
capture targets, pulls both configuration repos concurrently, warns about dirty
home sources, pushes ahead commits concurrently, then applies home followed by
system configuration. Both repos are required. Capture validates every result
before writing any source. Fcitx capture retains its existing private backup
behavior. Git uses `pull --rebase --autostash`; unknown upstream state is an
error. Each repository's Git operation holds a local lock, so overlapping
Tjikup runs wait instead of changing the same worktree during a rebase. A
configuration-refresh warning stops subsequent apply stages.

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

The installer does not commit, pull, push, capture settings or apply either
configuration repo. It checks the system adapter exists, installs the executable
and icon, validates the workflow, and atomically links the default configuration.
It can also be run before the first home apply once Chezetc is initialized.

The managed installation hook and focused installer select `$TOOLTJIK_REPO`, an existing
`~/code/tooltjik`, or `~/.local/share/tooltjik`. If absent they clone tooltjik.
The installer builds and installs only tjikup, leaving other applications alone. Existing
checkouts are not pulled by this hook; update tooltjik explicitly before
applying to deploy a new runner version, for example:

```sh
git -C ~/code/tooltjik pull --ff-only
TOOLTJIK_REPO=~/code/tooltjik bash ~/.local/share/chezmoi/scripts/install-tjikup.sh
```

Use `~/.local/share/tooltjik` instead on devices with the default cloned checkout. It fails clearly if the checkout does
not yet contain tjikup. The command and notification icon are tooltjik-owned;
Chezmoi no longer installs runner code into `~/.local/lib/tjikup`. An old copy
there is unused by the new self-contained executable and may be removed after
migration. No blanket apply is needed to migrate the command.

Setup hooks render colored pending and completion rows directly, including during
a plain `chezmoi apply`. They do not use Gum spinners, whose terminal capability
queries can leave echoed replies in the output when stdin is redirected.

## Use and validation

```sh
tjikup                         # use the installed fleet configuration
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
