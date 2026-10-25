# Essential configuration restoration plan

Status: remaining application work is proposed. Zen was dropped in favor of its
own sync. Telegram's successful minimal-settings trial is recorded below, with
its proposed entry kept separately in `docs/telegram-settings-policy.json` pending
upload approval. The subsequent existing-archive cache cleanup and compact
codex-lb recovery rollout are documented in `device-archives.md` and the dated
content audit; they do not activate Telegram backups.

The goal is to recover application choices and customizations after reinstalling
software. Downloadable software, caches, browsing history, login sessions,
website storage, game installations and game saves are outside this plan.
Exclusion from these backups does not delete anything from the source.

## Findings and scope

Some README TODOs are stale or partly implemented:

- `home/dot_config/direnv/direnvrc` already defines `layout_uv`, and Fish loads
  the direnv hook. The helper needs verification and hardening.
- Zen previously had a config-only archive rule; the new policy removes it by
  user preference. Existing remote archives are retained. Sync coverage has not
  been audited as part of this work.
- Chezetc already has a laptop branch in `etc/fstab.tmpl`. Its UUIDs still need
  comparison with Li's actual disks.
- Fi's `.config/uv` currently contains a downloaded Python runtime, with no
  `uv.toml`. There is no configuration there to capture today.

| Directory | Current disk usage on Fi | Candidate config payload |
| --- | ---: | ---: |
| `.zen` | 4.6 GiB | Out of scope; use Zen sync |
| `.config/BraveSoftware` | 683 MiB | 219.2 KiB |
| `.config/Steam` | 9.0 GiB | 87.7 KiB |
| `.config/uv` | 84 MiB | None currently |
| `.local/share/firefoxpwa` | 829 MiB | 44.2 KiB |
| `.local/share/TelegramDesktop` | 2.3 GiB | 42.4 KiB: global settings, shortcuts and palette |

Directory totals are rounded `du` disk usage; candidate sizes are sums of
regular-file lengths, uncompressed, using the archive tool's pattern matcher.
They are not directly equivalent storage measurements. The candidate payload
is approximately 0.4 MiB after dropping Zen; this excludes Telegram account
settings, optional Steam artwork/controller customizations, and later additions.

## Storage and selection rules

Use Chezmoi for authored, non-sensitive text configuration and installation
instructions. Use the existing encrypted `device-archives` workflow for
application-written settings: `mode: device`, `devices: [clients]`,
`encrypted: true`, `retention: daily-weekly-monthly`. Each client retains its
own settings; these additions must not create cross-device synchronization or
new initial-sync requirements. Si receives none of these desktop archives.

The existing retention scheme means at most three snapshots: latest, previous
ISO week, and previous calendar month. Reuse the existing schedule and verified
upload/readback mechanism described in [device-archives.md](device-archives.md).

Select explicit files with `include_files`. New files should be excluded by
default. Do not recursively `chezmoi add` any of these application roots, use
`*.json`/`*.vdf` across a whole profile, or treat all of `config/` as safe.
Preferences can contain private URLs and account metadata; keep raw app state
out of Git even when it is small.

Add exclusions for known cache/runtime trees to avoid needless traversal. The
current scanner filters files but still walks unselected directories; consider
pruning directories that cannot match any allowlist pattern, with tests for
nested profiles and trailing `**`. Do not introduce a silent size cutoff that
could discard an essential setting. A dry-run inventory should report selected
file count, bytes, and unexpectedly large files before a policy is activated.

## Per-item implementation

### 1. Direnv and uv — implemented

Implemented in `home/dot_config/direnv/direnvrc`:

- Resolve the current project's `.venv` deterministically, ignoring an inherited
  `VIRTUAL_ENV` belonging to another project.
- Verify `uv` exists and stop on failed environment creation before exporting
  `VIRTUAL_ENV` or updating `PATH`.
- Watch `pyproject.toml`, `uv.lock`, and `.python-version` where present. Keep
  dependency installation explicit through `uv sync`; entering a directory
  should not silently rewrite a lockfile or install project dependencies.
- Document a project `.envrc` using `layout uv`, followed by `direnv allow`.
  Preserve project manifests, lockfiles and Python pins in their project repos.
- Manage `~/.config/uv/uv.toml` only if actual user settings are needed. Audit
  any existing config for private index credentials before adding it to Git;
  credentials belong in a separate secret source or encrypted archive.
- Exclude `.config/uv/python/`, uv caches, downloaded interpreters, installed
  tools and virtual environments. Reinstall them from the package/project
  declarations. Do not invent an empty uv backup just to close the TODO.

Acceptance: isolated shell tests cover new/existing environments, inherited
environments, paths with spaces, missing uv and failed `uv venv`. A temporary
project verifies enter/leave behavior and explicit `uv sync` after rendering.

### 2. Zen — no further integration

Use Zen's own sync, as requested. Remove `.zen` from the scheduled device archive
policy without deleting existing snapshots. No workspace-format investigation,
additional allowlist entries or Zen restore implementation is planned. This
choice does not assert that Zen sync covers every local customization.

### 3. Brave

Create an archive entry rooted at `.config/BraveSoftware/Brave-Browser`:

```text
Local State
Default/Preferences
Default/Secure Preferences
Profile */Preferences
Profile */Secure Preferences
NativeMessagingHosts/*.json
```

Exclude all caches, component downloads, extension binaries, `BraveWallet`,
`Sessions`, `History`, `Cookies`, `Login Data`, `Web Data`, `Local Storage`,
`IndexedDB`, service workers and extension storage. Do not automatically include
`Bookmarks`; that is a separate user-data recovery decision.

These preference files may retain machine-specific values and private account
metadata. Keep them encrypted and restore with Brave stopped. Test profile
discovery and actual preferences in a separate user-data directory: Chromium
may reject protected preferences after migration, and this file set does not
promise to restore installed extensions or authentication. Document any
settings that require reapplication instead of expanding to a full profile.

### 4. Steam

Fi's real Steam root is `.config/Steam`; `.steam/root` and `.steam/steam` point
there. Archive it once, without following the compatibility symlinks:

```text
config/config.vdf
config/libraryfolders.vdf
steamapps/libraryfolders.vdf
userdata/*/config/localconfig.vdf
userdata/*/config/shortcuts.vdf
userdata/*/config/compat.vdf
```

Inventory user-authored controller mappings and shortcut artwork separately.
Add exact paths only if they hold customizations that cannot be regenerated;
do not include all of `userdata/` or a generic controller/cache tree. Inspect
the small `.steam/registry.vdf` and `exportedsettings.json` separately to decide
whether either contains unique user settings before adding another archive root.

Exclude `config/htmlcache`, `appcache`, logs, packages, runtimes, game binaries,
downloads, shader caches, Workshop downloads and Proton prefixes. Exclude
`loginusers.vdf`, authentication tokens and `ssfn*` session files. Game saves
in `userdata/*/<appid>/remote` or `steamapps/compatdata` are persistent data, not
caches, but are outside this configuration-only plan. Do not claim Steam Cloud
covers every game save.

Acceptance: after reinstall and fresh login, restore with Steam stopped and
check client options, launch/compatibility settings and non-Steam shortcuts.
Reconcile library paths and account IDs for the destination; library manifests
do not restore games. Verify any selected custom mappings/artwork separately.

### 5. FirefoxPWA

Create an archive entry rooted at `.local/share/firefoxpwa`:

```text
config.json
profiles/*/prefs.js
profiles/*/user.js
profiles/*/containers.json
profiles/*/handlers.json
profiles/*/search.json.mozlz4
profiles/*/persdict.dat
```

Fi's `config.json` contains profile/site registrations, arguments, variables
and config. Preserve profile/site identifiers and inspect destination-specific
paths on restore. Do not print private URLs or variable values into reports.

Exclude `runtime/`, logs, profile caches, website storage, cookies, passwords,
history, sessions and installed extensions. `profiles/*/chrome/pwa/` is installed
integration code: regenerate it. Inspect `chrome/userChrome.css` and any other
overrides for actual user edits before selecting exact files; do not capture
the entire `chrome/` tree as customization.

Acceptance: reinstall FirefoxPWA and its runtime, restore registration/settings
with all PWA processes stopped, and use the installed version's supported site
update/integration flow to regenerate desktop entries and icons. Confirm that
registered apps appear and launch. Fresh website login is expected. Verify the
precise integration command during implementation rather than assume copying
`config.json` alone recreates launchers.

### 6. Telegram Desktop — minimal trial implemented

The separate Telegram proposal selects only root-level global settings slots
(`settingss`, `settings0`, `settings1`), `shortcuts-custom.json`, and exported
`*.tdesktop-palette`/`*.tdesktop-theme` files from
`.local/share/TelegramDesktop/tdata`. On Fi this is three files, 43,399 bytes.
The proposed client-only archive is encrypted and independent per device, with the
existing daily/weekly/monthly retention.

The matching Telegram 7.3.3 source confirms global settings derive their key
from the salt inside the settings file. An isolated startup successfully read
and decrypted Fi's copied settings without `key_datas` or account files. The
repeat trial used a private display, disabled networking and a read-only live
filesystem; source files were unchanged during that repeat. The trial process
was then terminated and its temporary files removed.

Theme/background blobs, account preferences and login sessions remain excluded.
Reimport the retained custom theme as needed. Login and visual/settings checks
remain manual; successful parsing does not prove every option is portable.
See [the Telegram restore instructions](device-archives.md#telegram-desktop-settings)
for exclusions and the exact restore procedure. Other plan items remain proposals.

### 7. Laptop fstab

Keep this in Chezetc, which already owns `/etc/fstab`. No home-directory backup
entry is needed. Compare the existing laptop branch with Li's `/etc/fstab`,
`findmnt` and filesystem UUID/subvolume inventory. Capture only actual mount
definitions; do not copy Fi's UUIDs or credentials into Li's configuration.

Validate a rendered candidate using `findmnt --verify --tab-file` on Li and
inspect referenced devices before any apply. Preserve installer-owned root,
boot and EFI entries when reinstalling onto different disks; old UUIDs are
recovery references, not portable defaults. Update/document the template only
where the comparison identifies a real mismatch. Preserve a before-image for
any eventual system change. Successful rendering alone does not prove boot or
mount behavior; verify those on the laptop during rollout.

## Delivery sequence and completion criteria

1. Inventory Li's installed apps and corresponding paths using filenames and
   sizes, without dumping private settings. Verify Telegram's limited global
   settings restore on Li; retain the documented account/theme limitations.
2. Harden direnv and add the proven app allowlists in
   `home/dot_config/archive-policy.json`. The policy recovery copy is rendered
   from this source. Keep new rules per-device and encrypted. Add traversal
   pruning only if it is needed to avoid repeatedly scanning large trees.
3. Extend `tests/test_device_archives.py` with realistic fixtures: multiple
   profiles/accounts, included customizations, excluded cache/runtime/session
   data, large unselected trees, missing apps and symlink roots. Verify omitted
   paths stay omitted in staging and restore; test that app updates cannot
   widen the selection accidentally. Add focused direnv tests.
4. Run focused tests and `bash scripts/validate.sh`. Render the affected policy
   and hooks for Fi, Li and Si; assert client assignments and no new Si app
   backups. Record selected counts/bytes per app before first backup. Report
   unexplained growth for review rather than silently losing selected files.
5. During implementation rollout, close the relevant apps for a consistent
   first snapshot, back up only the selected folders, and verify encrypted
   remote readback. Restore to a temporary directory, compare the manifest,
   and perform the app-specific restore checks above. Static tests and archive
   integrity alone are not application acceptance.
6. Update README TODOs to distinguish completed, intentionally unnecessary,
   and unresolved items. Zen and Telegram policy documentation has been updated;
   document the other applications as their implementation and restore checks
   are completed.

Completion means demonstrable configuration recovery with the selected payload,
plus explicit exclusions. It does not mean every application directory is
backed up or that every prior login, tab, game save or downloaded file returns.
