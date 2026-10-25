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
error. A configuration-refresh warning stops subsequent apply stages.

## Installation and migration

Publish/install the matching revisions of tooltjik, dotfiles and Chezetc together.
Until these changes are published, use the existing local tooltjik checkout:

```sh
bash ~/code/tooltjik/apps/tjikup/scripts/install.sh
tjikup --config ~/.local/share/chezmoi/tjikup.json --check
chezmoi apply --exclude=scripts ~/.config/tjikup/config.json
```

`~/.config/tjikup/config.json` links to the workflow in the dotfiles source.
Changing the workflow changes the next invocation. A run loads the configuration
once, before any scripts execute. Pulls may update subsequent scripts, matching
the existing fleet update behavior.

The managed installation hook selects `$TOOLTJIK_REPO`, an existing
`~/code/tooltjik`, or `~/.local/share/tooltjik`. If absent it clones tooltjik.
It builds and installs only tjikup, leaving other applications alone. Existing
checkouts are not pulled by this hook; update tooltjik explicitly before
applying to deploy a new runner version. It fails clearly if the checkout does
not yet contain tjikup. The command and notification icon are tooltjik-owned;
Chezmoi no longer installs runner code into `~/.local/lib/tjikup`. An old copy
there is unused by the new self-contained executable and may be removed after
migration. No blanket apply is needed to migrate the command.

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
