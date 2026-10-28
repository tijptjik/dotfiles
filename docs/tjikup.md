# Tjikup recipes

Tjikup is a Rust recipe runner in tjikOS. This repository supplies declarative
recipes and application commands. The runner has no Python library API.

The root workflow is Dotjik's `tjikup.json`. It declares prerequisites, exact
capture/autocommit files, repository synchronization, and explicit home/system
configuration managers. It includes `tjikup/recipes.json` and `system/tjikup/recipes.json` from this checkout.
The graph preserves shared resource exclusion and final service/network/release
ordering across home and system tasks.

Regular maintenance templates now live in `.chezmoitemplates/tjikup` under the
managed source root. They are not Chezmoi hooks. Tjikup renders and syntax-checks
them, then executes recipes. Plain `chezmoi apply` / `chezetc apply` no longer runs
these maintenance tasks. Native initial bootstrap/once/onchange hooks remain for
explicit bootstrap; Tjikup's file actions exclude scripts entirely. Recurring
Bitwarden CLI and font preparation are explicit Tjikup recipes.

Install the consolidated dotfiles changes and the Rust runner together. From Dotjik:

```sh
bash scripts/install-tjikup.sh
tjikup --check
tjikup --plan
```

The installer validates the full graph before replacing the executable. Cargo
is required to build from source. Initial provisioning still follows the existing
bootstrap guides; install prerequisites and initialize Chezmoi and Bitwarden credentials before
running the fleet workflow. Tjikup does not silently bootstrap missing managers,
passwordless sudo, secrets or upstream branches.

`--dry-run` is now a strictly nonexecuting plan. `--upgrade` retains the package
upgrade policy. `--skip-conflicts` preserves conflicting files. `--skip-repo-sync` bypasses
repository pulls/pushes and their clean-worktree checks while retaining capture
and its scoped commit; both switches are declarative workflow policy. Missing checkouts,
detached branches and absent upstreams now fail explicitly before file apply.
If a pull changes recipe configuration, rerun Tjikup to use the new graph.

Capture remains a standalone Python command with the existing template-aware
propagators and private backups. It has no dependency on the runner's internals.
Autocommit and Git orchestration are native Rust actions, and only the explicitly
listed tracked files may be automatically committed. Unrelated work is preserved.

Logs and timing receipts are private under `~/.local/state/tjikup/logs`. No live
apply is part of tests. Test recipe rendering for fi/li/si, then perform a
supervised update before treating the migration as live acceptance.

The complete schema and execution contract are documented in
[tjikOS](https://github.com/tijptjik/tjikos/tree/main/apps/tjikup).

## Git-only shortcuts

Available on `fi`, `li`, and `si`, from any working directory and shell:

```sh
tjix                 # push committed changes in Dotjik and tjikOS
tjixx                # pull both with rebase, then push both
tjix --dry-run       # show repositories and commands, without network or writes
tjixx --dry-run      # also check that both working trees are clean
tjix --verbose      # include repository paths and successful Git output
dotjik diff          # native home file plan
systjik diff         # native system plan on Fi; legacy file diff on Li/Si
```

Dotjik (`tijptjik/dotfiles`) owns home and system configuration. Systjik's source
and uncommitted changes now live under `system/`; its separate checkout is a
recovery copy, not another sync target. `systjik` and `chezetc` are compatibility
commands for file check/plan/diff/apply. Maintenance tasks run through `tjikup`.

The shortcuts synchronize this host's two checkouts. They do not commit new work,
capture live settings, apply configuration, install tools, or contact other fleet
hosts. `tjikup` remains the full update workflow. Push-only `tjix` permits dirty
files but sends only committed history. `tjixx` requires both working trees
(including untracked files) to be clean; commit or stash intentionally beforehand.
It explicitly uses `git pull --rebase --no-autostash`, so it never temporarily
hides ongoing work. It checks every repository before any network operation,
pulls both concurrently before pushing both concurrently. Every pull
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
rebase temporarily detaches HEAD. After checking both repositories, they run
`git rebase --continue` with the existing commit message. Resolve conflicts and
stage the intended resolutions with `git add` first; the shortcuts never stage,
skip, abort, or amend automatically. A clean pause at an edit step can also
continue. Unresolved conflicts or unstaged edits stop the command with guidance.
If continuation hits another conflict or pause, no repositories are pushed;
inspect the rebase, finish the next resolution and rerun. `--dry-run` only reports
the planned continuation. Other unfinished Git operations still require manual
completion. Ordinary detached HEAD checkouts are not pushed.

Dotjik is located via `chezmoi source-path` and its Git root. Both Git-only shortcuts, the full `tjikup` workflow,
and app installers target tjikOS at `~/code/tjikos` (`tijptjik/tjikos`). Set
`TJIKOS_REPO` to select another checkout. The retired `TOOLTJIK_REPO` override
and existing Tooltjik directories are not selected automatically.
`DOTJIK_REPO` overrides the dotfiles path. `SYSTJIK_REPO` is set by the workflow to its `system/` directory. Missing
checkouts fail clearly rather than being cloned. The shortcuts share Tjikup's
workflow and repository locks and report a busy checkout instead of racing it.
Git settings are passed per invocation; no global Git configuration is changed.

To install only the commands, without running provisioning hooks:

```sh
chezmoi apply --include=files ~/.local/bin/tjix ~/.local/bin/tjixx \
  ~/.local/bin/dotjik ~/.local/bin/systjik ~/.local/lib/tjik_git.py
```

## Native file migration

Fi uses `system/native/fi/manifest.json` for 18 system targets: 14 files,
two symlinks and two absent targets. Native home credentials are declared in
`native/home/{fi,li,si}.json`: seven Fi files, five Li files and two Si files.
The old home sources remain in the checkout for migration comparison and recovery;
`home/.chezmoiignore` excludes every target. Old removal and external-repository
rules are disabled, with equivalents declared in native policy. All remaining home files now use `native/home/files.json` with host context in
`native/home/files-{fi,li,si}.json`. This includes Zed, Herdr and Docker templates.
Only maintenance-task templates and Li/Si system templates still use Chezmoi.

The first home apply checks each existing credential against its old Chezmoi
render before adopting it, without target writes. Divergent local files block
migration. Create-only Drive credentials preserve refreshed local content.
Subsequent native applies use recorded hashes and reject unrecorded edits.
Fish credentials use literal quoting and all native credentials use mode `0600`.
The Bitwarden token stays in `~/.config/bws/environment` with mode `0600`;
`BWS_ACCESS_TOKEN` may also be supplied in the environment. Authentication uses
the existing Bitwarden Secrets Manager machine token and `/usr/local/bin/bws`.

```sh
python3 scripts/native-files.py home plan
python3 scripts/native-files.py home apply
python3 scripts/native-files.py system plan
python3 scripts/native-files.py system apply
```

These commands only manage files. System operations retain an explicit sudo
boundary. Home state lives in `~/.local/state/tjikup/files/home`; system state
lives in `/var/lib/tjikup/files`. Replacements have private backups and receipts;
`tjikup files restore --receipt PATH --state-dir STATE` restores only unchanged
post-apply targets. Backups contain private plaintext: never commit them.
The initial home plan may report unmanaged-file conflicts until guarded adoption
runs during apply. No blanket force flag is provided.

`scripts/legacy-system.py` supplies deterministic configuration directly to
Chezmoi for remaining system rendering. `/opt/chezetc` is no longer required.
`system/setup.sh` installs the unified runner and compatibility command; it does
not provision packages. Historical server bootstrap guides still need deliberate
host-specific review before use. Keep the old Systjik checkout and its Git history
as a recovery copy until the consolidated changes are committed and backed up.

Runner repository rows retain pulled/pushed commit totals in the status column
(`↓3 ↑2`); skipped, failed or unmeasured operations use `–`.

## Home files and captured settings

The authoritative home tree is `native/home/files/`, using destination-style names.
Templates end in `.j2` and use strict MiniJinja expressions. Static files remain
literal, even when they contain another application's template syntax. Shared
entry definitions in `native/home/files.json` declare modes, private directories,
symlink targets, host selection and retired paths. Standalone credentials retain
their earlier `native/home/{host}.json` manifests and state IDs.

Fi's general manifest covers 744 targets: 374 regular files, 243 symlinks,
111 directories and 16 removals. Together with its seven standalone credential
files, 751 home targets belong to Tjikup. Li and Si use their own conditions and
home directories; no local validation claims a remote deployment.

```sh
dotjik plan                    # both native home manifests
dotjik apply                   # files only; no packages, Git sync or service tasks
dotjik edit ~/.config/zed/settings.json
dotjik source-path ~/.config/fish/config.fish
python3 scripts/native-files.py home-files check
```

New files require an explicit entry in `native/home/files.json`; the old `add`
operation is not an automatic file importer. `dotjik diff` is a metadata-only
native plan and never prints secret content. `cm`, `ce`, apply/diff shortcuts and
configuration-editing aliases now use Dotjik's native file commands.

Capture writes to the native sources and `native/home/data/`, and the scoped
capture commit whitelist follows those paths. Zed capture protects Jinja control
blocks and secret expressions; Herdr preserves `{{ user.home }}` expressions.
GTK settings take their current icon theme from a private runtime context file,
so applying base settings preserves a user's selected theme. Docker's secret
strings use `compose_quote` to keep literal dollar signs through Compose parsing,
and its rendered configuration is private (`0600`).

Icon generators write SVG sources into the native tree and declare aliases in
`files.json`. New icons inherit their registered directory's host condition;
retired icons become explicit removals. Generator checks and release receipts
include native ownership. A new theme directory needs explicit manifest policy
before generation; generation does not approve artwork or apply home changes.

Identical live files are adopted without writes. First-use metadata differences
are accepted only after comparing the current bytes with their original source
or Go template. Unknown local changes stop migration. Once adopted, normal native
drift checks protect local edits. Directories are never recursively deleted.
Existing private backup receipts and `tjikup files restore` remain the recovery
mechanism for intentional changes.

`native/home/repositories.json` replaces the old Obsidian external declaration.
The `home:repositories` recipe creates missing checkouts and preserves existing
Git work. `home:files` no longer invokes Chezmoi; the remaining home manager only
renders maintenance recipes. Install the matching runner before enabling this
workflow on another host:

```sh
bash scripts/install-tjikup.sh
tjikup --check
tjikup --plan
```
