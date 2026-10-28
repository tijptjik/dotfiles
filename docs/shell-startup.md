# Fish startup

Fish automatically reads `conf.d/*.fish` before `config.fish`. Do not source
these files again from `config.fish`: that repeats aliases, prompt hooks,
external commands, and PATH maintenance.

`00-environment.fish` loads shared variables before the remaining snippets.
The variables file has a per-shell guard so Fish's later automatic load is a
no-op. Keep that guard unexported so child shells initialize their own settings.

`config.fish` activates the Python environment, then prunes stale project
bins and selects the current worktree's bin directory once. Directory changes
continue to update the project bin through the PWD event handler. PATH cleanup
only asks Git about bin directories whose parent has a `.git` entry, including
linked worktrees, instead of spawning Git for every PATH entry.

The renderer was renamed from `pony-rs` to `greetjik`.
The automatic greeting runs `fortune | greetjik` once per interactive terminal.
Each shell gets a newly selected fortune and pony. The Rust renderer is installed
from `tjikos/apps/greetjik` by `scripts/install-greetjik.sh` and the client-only
`run_after_38-install-greetjik` hook. The hook provisions Cargo and fortune-mod
when missing. `pony` is also available on demand; it prefers greetjik and can use
a native ponysay installation as a manual fallback. Startup skips the greeting
if either greetjik or fortune is missing, and never starts Docker.

The Rust app embeds the complete pinned upstream catalogue (474 regular and 103
extra ponies, each with a TTY variant). It accepts quotes on stdin, preserves ANSI
artwork, and handles Unicode text. Rendering needs no resident process, Python,
network request, cache refresh, or filesystem artwork lookup. Artwork licensing
and attribution remain in `tjikos/apps/greetjik/assets`. Ghostty provisioning was
removed; Kitty remains the managed terminal.

## Validation and measurements

Run `python3 -B -m unittest discover -s tests -p 'test_fish_*.py' -v` to check
project-bin cleanup, worktree switching, and the greeting. Apply the affected
Fish files with `chezmoi apply --exclude scripts <target paths>`.

On 2026-10-27, launches from the home directory on the local Wayland session
measured process start through completion of the first interactive Fish prompt.
This first comparison was made before restoring the native pony greeting.
Both terminals used their existing configuration, fresh processes, two warm-up
launches, and 12 measured launches each in alternating order. These measurements
use warm filesystem caches and do not measure first-frame presentation.

| Terminal | Previous median | Updated median | Updated range |
| --- | ---: | ---: | ---: |
| Kitty 0.49.2 | 2.321 s | 0.720 s | 0.631–0.810 s |
| Ghostty 1.3.1 | 2.649 s | 0.797 s | 0.741–0.882 s |

For diagnosis, Fish supports `--profile-startup=<path>` and `--profile=<path>`.
Exit the profiled shell normally to flush the reports. Profiles can contain
expanded secret assignments; keep them private and delete them after inspection.

## Native Rust greeting

`greetjik` replaces the Docker-based greeting. On this machine, 30 standalone
random-pony renders with piped text had a median of 2.33 ms (1.30–2.81 ms),
including process launch. The old native Python zip launcher took approximately
200–230 ms, and launching its Docker container cost around one second.

Use `fortune | greetjik`, `greetjik -f twilight 'Hello'`, or `greetjik --all --list`.
Extras with names shared by regular ponies can be selected with
`greetjik --extra -f NAME`. No persistent background pony service is needed.

With the native greeting deployed, a subsequent same-method Kitty benchmark
(two warm-ups and 12 measured launches) reached the first prompt in a median
310 ms, with a 288–331 ms range. A real Kitty window was also checked for the
visible fortune, coloured pony, and prompt. System load and caches differ across
runs; the standalone renderer benchmark isolates its own cost.

## Docker comparison and reproducibility

A later controlled comparison used the same `twilight` pony and fixed quote,
with an already-running Docker daemon and cached image. After two warm-ups,
12 alternating samples per implementation measured median quote-to-output times
of **479.20 ms for Docker** and **1.27 ms for greetjik** (about 378x faster for this
pipeline). This excludes fortune generation, Fish initialization, and display
presentation; it does not claim a 378x whole-terminal improvement.

The [greetjik guide](https://github.com/tijptjik/tjikos/tree/main/apps/greetjik)
contains usage, artwork coverage and licensing, the reproducible benchmark
runner, and raw timing records. Bun was upgraded locally to **1.4.4** and the
tjikOS package-manager pin now matches it; frozen-lockfile installation and
the greetjik Turborepo build/check both pass.
