# Repository Guidelines

## Response summaries

- Preface every final summary response with "# SUMMARY `r{sequence}`" with `{sequence}` is an auto-incrementing number.

## Project Structure & Module Organization

This repository owns home and system policy for Tjikup. Native manifests live in `native/` and `system/native/`; Maintenance templates live in `native/tasks/` and render through Tjikup MiniJinja. System recipes and sources live under `system/`. `.chezmoiroot` selects `home/` as the source root. Authoritative home configuration lives in `native/home/files/` with ordinary destination names and `.j2` templates. `native/home/files.json` declares ownership and host conditions; captured JSON data lives in `native/home/data/`. The old `home/` file sources are retained only for migration comparison. Chezmoi hooks, shared data, and helpers live in `home/.chezmoiscripts/`, `home/.chezmoidata/`, and `home/.chezmoihelpers/`. Docker service definitions and assets live in `home/dockers/`. Use `docs/` for topic guides, `tests/` for regression tests, and `scripts/` for repository tooling.

## Development & Validation Commands

There is no application build step. Run commands from the repository root:

- `bash scripts/validate.sh`: check Python syntax, non-template Bash/Fish syntax, and run regression tests; requires Python 3 and Fish.
- `python3 -B -m unittest discover -s tests -v`: run the full test suite.
- `python3 -B -m unittest discover -s tests -p 'test_tjikup.py' -v`: run focused tests.
- `dotjik plan`: inspect pending native file changes without displaying contents.
- `dotjik apply`: apply declared home files only; tasks run through Tjikup.
- `tjikup --dry-run`: preview supported live-configuration synchronization. Ordinary `tjikup` also commits, pulls, pushes, and applies changes.

## Coding Style & Naming Conventions

Follow surrounding formatting; use four-space indentation and snake_case names in Python. Preserve Chezmoi attributes: `dot_` represents a leading dot, `executable_` marks executable files, `private_` controls permissions, and `.tmpl` marks Go templates. Keep host-specific logic in native templates and shared values in explicit native JSON context. The validation script checks syntax; it does not enforce a repository-wide formatter.

## Testing Guidelines

Tests use standard-library `unittest`, `test_*.py` files, and `test_*` methods. Add regression coverage for changed behavior using temporary directories and mocked external commands. Keep tests isolated from live dotfiles, secrets, and Git remotes. No numeric coverage threshold is configured. Validation excludes shell templates; check rendering and affected host behavior separately for `fi` (desktop), `li` (laptop), and `si` (server).

## Commit & Pull Request Guidelines

History includes imperative summaries and scoped Conventional Commits such as `fix(homepage): correct labels`.

## Configuration & Secrets

Keep credentials out of committed files and rendered examples. Update the relevant topic guide when changing operational workflows.
