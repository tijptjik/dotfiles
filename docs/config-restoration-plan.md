# Essential configuration restoration

Status (2026-10-25): minimal Telegram, Brave, Steam and FirefoxPWA backups are
implemented and deployed on Fi and Li. Zen is delegated to its own sync.
`layout_uv` is hardened and tested. Li's managed fstab matches its actual disks
and mounts; no change was necessary. The original proposed selections below
are now implemented, with explicit FirefoxPWA CSS overrides added after review.
The user accepted best-effort recovery for Brave, Steam and FirefoxPWA; GUI
restore acceptance for those apps was not required. Telegram's post-login
settings check found a dark-mode regression; the corrected theme dependency
selection and its startup verification are recorded below.

The goal is to recover application choices and customizations after reinstalling
software. Downloadable software, caches, browsing history, login sessions,
website storage, game installations and game saves are outside this plan.
Exclusion from these backups does not delete anything from the source.

## Findings and scope

The original README TODOs are now resolved as follows:

- `native/home/files/.config/direnv/direnvrc` already defines `layout_uv`, and Fish loads
  the direnv hook. The helper now validates uv, ignores inherited environments,
  and watches
  `pyproject.toml`, `uv.lock` and `.python-version`.
- Zen previously had a config-only archive rule; the new policy removes it by
  user preference. Existing remote archives are retained. Sync coverage has not
  been audited as part of this work.
- Tjikup already has a laptop branch in `etc/fstab.tmpl`. Its UUIDs and
  subvolumes match Li's actual disks;
  both the rendered file and current local laptop branch passed validation.
- Fi's `.config/uv` currently contains a downloaded Python runtime, with no
  `uv.toml`. There is no configuration there to capture today.

| Directory | Initial disk usage on Fi | Initial candidate payload |
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

Use Tjikup for authored, non-sensitive text configuration and installation
instructions. Use the existing encrypted `device-archives` workflow for
application-written settings: `mode: device`, `devices: [clients]`,
`encrypted: true`, `retention: daily-weekly-monthly`. Each client retains its
own settings; these additions must not create cross-device synchronization or
new initial-sync requirements. Si receives none of these desktop archives.

The existing retention scheme means at most three snapshots: latest, previous
ISO week, and previous calendar month. Reuse the existing schedule and verified
upload/readback mechanism described in [device-archives.md](device-archives.md).

Select explicit files with `include_files`. New files should be excluded by
default. Do not recursively `declare in native/home/files.json` any of these application roots, use
`*.json`/`*.vdf` across a whole profile, or treat all of `config/` as safe.
Preferences can contain private URLs and account metadata; keep raw app state
out of Git even when it is small.

Exclusions remove known cache/runtime trees. The scanner now prunes directories
that cannot match any allowlist pattern, with regression coverage for nested
profiles, trailing `**`, and unselected trees that must never be traversed.
Do not introduce a silent size cutoff that could discard an essential setting. A dry-run inventory should report selected
file count, bytes, and unexpectedly large files before a policy is activated.

## Per-item implementation

### 1. Direnv and uv — implemented

Implemented in `native/home/files/.config/direnv/direnvrc`:

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

### 3. Brave — enabled

The active archive entry is rooted at `.config/BraveSoftware/Brave-Browser`:

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

### 4. Steam — enabled

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

### 5. FirefoxPWA — enabled

The active archive entry is rooted at `.local/share/firefoxpwa`:

```text
config.json
profiles/*/prefs.js
profiles/*/user.js
profiles/*/containers.json
profiles/*/handlers.json
profiles/*/search.json.mozlz4
profiles/*/persdict.dat
profiles/*/chrome/userChrome.css
profiles/*/chrome/userContent.css
```

Fi's `config.json` contains profile/site registrations, arguments, variables
and config. Preserve profile/site identifiers and inspect destination-specific
paths on restore. Do not print private URLs or variable values into reports.

Exclude `runtime/`, logs, profile caches, website storage, cookies, passwords,
history, sessions and installed extensions. `profiles/*/chrome/pwa/` is installed
integration code: regenerate it. Fi has a 97-byte `chrome/userChrome.css` override hiding browser chrome.
Retain the exact userChrome/userContent override paths; the entire `chrome/`
tree is not selected.

Acceptance: reinstall FirefoxPWA and its runtime, restore registration/settings
with all PWA processes stopped, and use the installed version's supported site
update/integration flow to regenerate desktop entries and icons. Confirm that
registered apps appear and launch. Fresh website login is expected. Verify the
precise integration command during implementation rather than assume copying
`config.json` alone recreates launchers.

### 6. Telegram Desktop — enabled

The active Telegram entry selects root-level global settings slots
(`settingss`, `settings0`, `settings1`), `shortcuts-custom.json`, and exported
`*.tdesktop-palette`/`*.tdesktop-theme` files from
`.local/share/TelegramDesktop/tdata`, plus the exact day/night theme files
referenced by global settings. The initial three-file selection was 43,399
bytes on Fi; its required theme definition adds about 641 KiB after removing
regenerable compiled caches from the recovery copy.
The client-only archive is encrypted and independent per device, with the
existing daily/weekly/monthly retention.

The matching Telegram 7.3.3 source confirms global settings derive their key
from the salt inside the settings file. An isolated startup successfully read
and decrypted Fi's copied settings without `key_datas` or account files. The
repeat trial used a private display, disabled networking and a read-only live
filesystem; source files were unchanged during that repeat. The trial process
was then terminated and its temporary files removed.

Account preferences, login sessions, unrelated theme blobs and separate chat
backgrounds remain excluded. The referenced day/night themes are required to
preserve appearance and are selected dynamically. Other login and settings
checks remain manual; successful parsing does not prove every option is portable.
See [the Telegram restore instructions](device-archives.md#telegram-desktop-settings)
for exclusions and the exact restore procedure. Brave, Steam and FirefoxPWA entries are also active.

### 7. Laptop fstab — verified, no changes needed

Keep this in Tjikup, which already owns `/etc/fstab`. No home-directory backup
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

## Recovery acceptance

The new app entries are configuration-only backups. They do not preserve every
login, browser tab, game save or downloaded file. Brave, Steam and FirefoxPWA
are best-effort restores at the user's request; no GUI restore test was needed
to enable their backups. Their downloaded archives still receive the normal
decryption, manifest and extraction checks.

Telegram's login and visual/settings checks require the user's participation.
A separate review was prepared from Fi's actual R2 snapshot at
`~/.local/state/device-archives/telegram-settings-review/work/tdata`. Run
`~/.local/state/device-archives/telegram-settings-review/launch.sh` from the
desktop session to launch it with isolated config/data/cache directories and a
distinct Telegram working directory. Sign in there, check shortcuts,
appearance, display/notification settings and download paths. This does not replace the live profile. The review is not itself
included in the backup policy. It may be removed after the check and after
quitting the review instance; retain the actual app's profile.


## Verification record — 2026-10-25

The changes were installed on Fi and Li with scoped Tjikup applies, excluding
hooks and retaining private before-images under
`~/.local/state/device-archives/app-config-rollout-20261025T*/`. Applications
were not restarted and no live account/profile directory was replaced.

`layout uv` passed five isolated failure/selection tests and a real temporary
project check on both Fi and Li: enter creates `.venv`, does not install dependencies, explicit
`uv sync --offline` succeeds, and leaving restores the inherited environment
and PATH. Use `layout uv` in `.envrc`, run `direnv allow`, then run `uv sync`
explicitly as needed. No empty uv configuration backup was introduced.

Li's Tjikup-rendered `/etc/fstab` exactly matched the live file. The current
local repository's laptop branch was also checked against Li. `findmnt
--verify --tab-file` reported no errors or warnings, and the active mounts
matched these devices:

| Target | Filesystem/source | UUID |
| --- | --- | --- |
| `/` | Btrfs `root` on `nvme0n1p3` | `6eff2c29-fe2e-41e9-ac4f-3a2319f85443` |
| `/home` | Btrfs `home` on `nvme0n1p3` | same as `/` |
| `/boot` | ext4 on `nvme0n1p2` | `1b5a9e2b-2a67-48bb-b442-bda8d188c54a` |
| `/boot/efi` | vfat on `nvme0n1p1` | `7859-8D4F` |

No fstab edits, remounts or reboot were necessary. Reinstallation onto different
disks still requires reconciling installer-generated UUIDs.


The four app archives were encrypted, uploaded and independently downloaded,
decrypted and restored into temporary directories on both Fi and Li. Each
restored tree matched its archived manifest. Source application profiles were
not replaced or synchronized.

| App | Fi selected files / bytes | Li selected files / bytes |
| --- | ---: | ---: |
| Telegram | 3 / 43,399 | 3 / 42,923 |
| Brave | 4 / 224,416 | 4 / 87,033 |
| Steam | 6 / 89,843 | 5 / 89,971 |
| FirefoxPWA | 6 / 45,301 | 6 / 42,675 |
| Total | **19 / 402,959** | **18 / 262,602** |

These are uncompressed file bytes, about 393.5 KiB and 256.4 KiB respectively;
remote archives are compressed before encryption. Adding the reviewed 97-byte
FirefoxPWA CSS overrides required one replacement snapshot per host. Normal
retention removed the superseded same-day versions after verified readback.
The archive policy recovery copy was updated with the new selections.

`bash scripts/validate.sh` passed all **164 tests**. New coverage checks the
allowlists using encrypted round trips, account/cache exclusion, client-only
assignment, skipped traversal of unselected trees, and uv failure handling.
The actual restore receipts are retained privately on each client at
`~/.local/state/device-archives/minimal-app-restore-verification.json`.
The initial Telegram review contained only three global-setting files. The
user reported that dark/light mode was not restored; the correction below
supersedes that selection and its original size estimate.


### Telegram appearance correction

The user's review exposed a real dependency: `settingss` stored night mode and
a theme key, but the initial policy omitted the file behind that key. Telegram
7.3.3's `InitialLoadTheme()` calls `clearTheme()` when the file cannot load;
`writeTheme()` then clears night mode. A retained exported palette does not
repair the missing reference automatically.

The policy now resolves exactly the current day/night references from global
settings. It validates their settings-key encryption, checksums and theme
structure, then compacts only the staged copy. The compact file keeps the
embedded definition and metadata while clearing generated colors/background
caches and checksums. Telegram regenerates these on startup. Normalized theme
fingerprints mean cache-only churn does not create another upload. Account encryption keys and account state
are not consulted. Unknown schemas or missing/oversized dependencies fail
closed. Source files are hashed again during scanning, and normal staging
checks detect changes during capture.

An isolated two-case test used the same original settings with networking
disabled and the live home directory hidden. Without the theme, Telegram
loaded settings but cleared night mode; with the compact theme, it loaded the definition, regenerated its cache
and kept night mode. Source files were unchanged. This tests real application
startup, not just archive extraction. The review's account files are preserved
when replacing only its global settings and required appearance files.


The correction passed **173 repository tests**, including nine dedicated
Telegram dependency cases. Fi's replacement archive was independently restored
from R2 into the existing review: only global settings, shortcuts, palette and
the referenced theme were replaced, with before-images retained. The review's
account and other files were hash-verified unchanged. The review was reopened;
the normal Telegram instance was untouched. Further visual acceptance remains
with the user.

Final compact backups and independent R2 restores succeeded on both clients:

| Host | Files | Total uncompressed bytes | Theme recovery bytes | Restored mode |
| --- | ---: | ---: | ---: | --- |
| Fi | 4 | 700,099 | 656,764 | Dark |
| Li | 4 | 699,543 | 656,620 | Dark |

Both restored theme files had empty generated caches and intact theme content.
Li's 18,182,236-byte source theme included a 17,523,254-byte background cache;
that cache is omitted from its 656,620-byte theme recovery file. Fi's source
theme was 1,314,684 bytes before compaction. Live themes were not changed.
Normal retention replaced the superseded same-day Telegram snapshots only
after successful readback. Receipts are stored privately on each client at
`~/.local/state/device-archives/telegram-theme-restore-verification.json`.
