# Reading Tjikup results

Rows describe individual tasks, not the whole workflow. A home or system file
row does not execute all the recipes in that scope. Parentheses are dimmed
qualifiers; the right column describes the result.

## Sections and ordering

- **Prerequisites** checks Python, Fish and sudo availability. A satisfied check
  says REQUIRE, without installing anything. Fish and sudo remain dependency
  gates, so a home-only run does not acquire a new sudo requirement.
- **Capture settings** reads supported live app settings back into declared
  repository files. **Commit captured settings** commits only those declared
  paths when capture changed them; it is not a general dirty-tree commit.
- **Preparation** renders native maintenance templates into private per-run
  scripts and syntax-checks them. Preparing a script does not execute it.
- **Repositories** configures COPR, Fedora/third-party package sources and
  Flatpak remotes. This is separate from the Git pull/push table.
- **Install applications**, **Configuration**, **Services**, **Package updates**
  and **Verification** distinguish presence checks, file application, service
  activation, software updates and post-update config checks.

Workers still run concurrently with dependency and resource protection. Settled
rows are grouped for the early phase before updates start, then again when
updates complete. Live activity remains visible; failures print immediately.
This avoids repeated headings caused solely by completion order without adding
section barriers that could deadlock cross-section dependencies.

Git pull/push counts remain in the status column. Zero means no commits moved;
unknown/skipped is not reported as zero. The redundant `(current)` text is gone.

`--show-skips` shows only selected tasks. Machines must enroll with
`tjikup new device` to declare their role and recipe subscriptions. Fi is
enrolled as a desktop; Li and Si require their own enrollment.
`--show-skips-and-other-devices` additionally lists excluded recipes, marked
`not selected for this device`; it never executes them.

## What the less obvious tasks do

| Row | Work performed |
| --- | --- |
| Home files | Applies the base group of the native home manifest. App-specific groups have separate rows. |
| System files | Checks/applies the host's native system-file manifest, not all system tasks. |
| Home secrets | Renders declared credential-backed home files using the native secrets/context providers. This is separate from ordinary home files; it does not print credentials. |
| Synctjik (Required collections) | With a Synctjik device profile, checks archive readiness and runs setup/readiness/scheduling when needed. With no profile it is a no-op. |
| NSS (System integration) | On Si, configures Name Service Switch/systemd shadow-account lookups for transient GDM users on supported Fedora releases. |
| Power (sleep policy) | On Si, compiles the managed dconf sleep policy without restarting GDM or the session. |
| Media (Permissions) | Enables Si's media-permissions maintenance timer. |
| SnapRAID (Status) | Checks readable parity-maintenance metadata; it does not start a parity sync. |
| Transmission (cleanup) | Enables Si's daily Transmission cleanup timer, not a client installation. |
| SnapRAID (notifications) | Enables Si's SnapRAID health/watchdog alert timer. |
| Docker (Autostart/Service) | Enables and starts the Docker daemon through systemd. The Docker icon identifies the managed application. |
| Assets (Rose Punk Icons) | Maintains theme metadata, legacy overrides/theme IDs and icon caches. Artwork files are managed by the home manifest. |
| Synctjik (private assets) | Creates the four local private folders, retires old whole-tree sync services, and enables private-sync/private-backup timers. Initial merges remain explicit. |
| Obsidian (Vault) | Ensures the declared `.obsidian` Git checkout exists; it does not reset local work. |
| Notjik/Bartjik activation | Enables the replacement service, starts it when a graphical session exists, and retires legacy Dunst/Waybar state. Already-ready setups skip. |
| Runtjik activation | Checks launcher integration and retires obsolete launcher units while preserving launched applications. |
| Backup schedule | Previously “Common Units”: user lingering, unit reload and the package-backup timer. |
| Desktop session services | Previously “Clients Units”: desktop helper enablement/start checks. Idle/nightlight choices are preserved. |
| Hyprlock | Enables the login-lock unit; it does not lock the session during apply. |
| Synctjik (Cloudflare backup) | A separate Restic backup timer, gated on credentials and a verified restore. Synctjik owns the engine; the timer name and restore gate are retained. |
| User services | Refreshes changed active managed service runtimes and timers. It skips inactive services and refuses oneshot jobs; it does not restart pinned archive workers. |
| Applications (Server) | Si's backup-gated Plex and Docker Compose application updater, with session/activity checks. |

Post-update Obsidian/Zed checks verify that updates did not damage managed
configuration. They now appear under **Verification**, explicitly marked
`(Configuration)`, with `verified` as their result. Verification may refresh an
active service whose runtime changed, but does not repeat unchanged service rows.

## New artwork

DuckDB, Hyprland, Bottom, Starship and Quickshell retain upstream vector geometry
with vendored provenance/licenses. Lazygit and Vivid are original functional
concepts: neither project exposed a standalone logo in the inspected source or
artwork catalog. Synctjik is a copper member of the Tjik family with sync arrows.
The editable SVGs and 32px sprites belong to the primary frameless set. No
secondary framed-set approval is implied by this addition.
