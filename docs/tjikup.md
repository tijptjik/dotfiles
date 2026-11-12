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

Gmail's PWA `userContent.css` is shared as a plain managed file in
`native/home/files/.local/share/firefoxpwa/profiles/00000000000000000000000000/chrome/`.
It is deployed by the Fi/Li/Si manifests and the portable client manifest. Edit
that source (or use `dotjik edit` with the live file path), synchronize the
Dotjik repository, then apply dotfiles on each device. Live CSS edits are not
automatically captured; native apply preserves drift for review. Restart all
Firefox PWAs to load CSS changes. Use Gmail's built-in dark theme for the
interface; the shared CSS recolors message content and the conversation/reply
surfaces, leaving navigation, menus and warning banners to Gmail.

The shared PWA `user.js` enables custom stylesheets and dark content defaults,
and disables manifest background overrides. It also disables Firefox's early
unstyled blank startup window (`browser.startup.blankWindow`); the real browser
window opens with the palette styles instead. `userChrome.css` and the initial
content canvas use the Rose Punk base `#191724`, so startup does not depend on
Gmail having loaded. These appearance-only files apply to the shared PWA profile;
`prefs.js` and other device/account state stay outside the managed source.
These rules manage only the two CSS files and appearance-only `user.js`; profile
directories, caches, sessions and credentials are not added to Git.
Synctjik continues to back up `userContent.css` under its existing encrypted,
per-device PWA policy.

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

PdfCraft and WordCraft installed as system Flatpak bundles are updated with the
existing `system:flatpak` subscription on desktops and laptops. Their dedicated
update recipes query GitHub's structured Releases API, select the matching
architecture's `.flatpak` asset, and verify its SHA-256 digest before installation.
The version comes from `tag_name`, not release-note text. These recipes skip apps
that are absent; they do not install PdfCraft or WordCraft on another device.
`--skip-package-updates` and configuration-only runs exclude them. Explicit first
installation is available through `tjikup workflow install pdfcraft` or
`tjikup workflow install wordcraft`.

The upstream ArtCraft OCI remote exists, but on 2026-11-04 its PdfCraft and
WordCraft indexes returned HTTP 503 because their GHCR images denied anonymous
access, and its catalog lagged GitHub Releases. The bundle policy therefore uses
`https://api.github.com/repos/storytold/APP/releases/latest` directly. Existing
Flatpak app IDs, installation scope, branch and user data are preserved. Reopen a
running application after an update to load the new version.
This policy requires `flatpak_bundle_installers: 1`; runner installation retains a
compatible local build until the published release advertises that capability.

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

### Monthly disk cleanup

The normal update workflow runs `reclaim-diskspace --automatic` after selected
package updates and the existing home/archive readiness steps, before the final
Fedora release-upgrade step. Tjikup's native
`interval_seconds: 2592000` skips it until 30 days after its last successful run.
The first run is due immediately. This is checked when Tjikup runs; it does not
create a separate timer. `--skip-package-updates` and file-only applies exclude it.

Automatic cleanup clears package/browser caches, thumbnails, closed Spotify's
media cache and unlocked systemd coredumps. It keeps Docker images, installed
packages, kernels, clipboard history and journal logs. Flatpak repair stays
manual. It runs as the normal user, using `sudo -n` for system caches.
`reclaim-diskspace --automatic --dry-run` previews this scope; invoking the
command without `--automatic` retains the full manual cleanup.

The workflow retains its existing locks and readiness gates. Tjikup also locks
each periodic recipe across configurations and atomically writes a private
success receipt under `$XDG_STATE_HOME/tjikup/periodic/` (default
`~/.local/state/tjikup/periodic/`). Failed, interrupted or deferred cleanup does
not advance the interval. Output reports the net free-space change on the home
and `/var` filesystems and the next due date; concurrent writes can affect that
space measurement. `--show-skips` displays the due date when cleanup is skipped.

This policy requires a Tjikup build advertising `periodic_recipes: 1`. Upgrade
the runner before applying this repository revision on another device.

`bash scripts/validate.sh` runs policy regression tests and renders maintenance
templates for Fi, Li and Si without executing them. Set `TJIKUP_BINARY` to the
binary under test. Native behavior tests live in TjikOS `apps/tjikup/tests` and
Rust module tests; fixtures never require live credentials or services.

Tjikup `tjikup-v0.2.0-bootstrap.8` publishes the native patched-source installer
and is checksum-pinned in TjikOS. The fleet installer requires
`patched_source_installers: 1` before replacing an installed runner. Espanso
updates apply the tracked Wayland startup patch before building and activating a
new version; incompatible upstream changes preserve the current executable.

`tjikup --version` includes a source revision on newer builds; `--build-info`
returns machine-readable provenance. The fleet installer retains a compatible
installed build when its source revision is a strict descendant of the pinned
release. It reports that choice without recording a false cache success, and
keeps the scheduled runtime aligned. Future native capability changes likewise require a published release and an
updated checksum pin before fleet distribution.

### Local file conflicts

Home and system file recipes reserve the terminal for conflict review. Choose
**Review difference**, **Keep local**, **Use managed**, or **Cancel**. Keep local
preserves that whole file until its managed version changes, while other files
continue to deploy. This accommodates application-written settings such as
Codex browser-service version paths without copying them back into shared policy.
Use managed retains a private recovery receipt. Sensitive previews appear only
on the terminal after explicitly requesting them. Unattended runs stop on new
conflicts; run `tjikup config home apply` interactively to resolve them.

This policy requires `native_file_review: 1`. The installer retains a compatible
local runner while awaiting a published release with that capability.
