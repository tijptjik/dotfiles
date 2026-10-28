# Repository Guidelines

## Response summaries

- Preface every final summary response with "# SUMMARY `r{sequence}`" where `{sequence}` is an auto-incrementing number.

## Project Structure & Module Organization

This directory is the system policy of the parent dotfiles repository. Fi files use native Tjikup; unported templates use the parent `scripts/legacy-system.py` adapter. `.chezmoiroot` selects `etc/` as the source root. Service configuration lives in directories such as `etc/nginx/`, `etc/ssh/`, and `etc/systemd/system/`; system utilities live in `etc/usr/local/`. Chezmoi hooks, shared data, templates, and helpers live in `etc/.chezmoiscripts/`, `etc/.chezmoidata/`, `etc/.chezmoitemplates/`, and `etc/.chezmoihelpers/`. Server provisioning and maintenance components live in `etc/si-*/`. `chezetc.toml` defines the configuration template, and `setup.sh` installs the wrapper and configuration. Use `scripts/` for repository tooling and `tests/` for regression tests. Operational guidance lives in `README.md`, `SERVER-BOOTSTRAP.md`, and `SERVER-REBUILD.md`.

## Development & Validation Commands

There is no application build step. Run commands from the repository root:

- `bash scripts/validate.sh`: check Bash and Fish syntax and run regression tests; requires Bash, Fish, and Python 3. When Chezmoi and its configuration are available, also render Fish hook templates for the current host and check their syntax without executing them. Missing rendering prerequisites are reported as skipped.
- `CHEZETC_CONFIG=/path/to/chezetc.toml bash scripts/validate.sh`: validate using an alternate Chezetc configuration.
- `python3 -B -m unittest discover -s tests -v`: run the full test suite.
- `python3 -B -m unittest discover -s tests -p 'test_setup.py' -v`: run focused setup tests; select the relevant test file for other changes.
- `chezetc diff`: inspect pending changes to managed system files.
- `chezetc apply`: apply system configuration and execute applicable hooks, which can update packages, build software, and change services. Inspect the target host and pending changes first.

Use `python3 ../scripts/native-files.py system plan|apply` for file operations and the parent Tjikup graph for tasks. Do not use the retired `/opt/chezetc` writer.

## Coding Style & Naming Conventions

Follow surrounding formatting; use four-space indentation and snake_case names in Python. Preserve Chezmoi attributes: `dot_` represents a leading dot, `executable_` marks executable files, `private_` controls permissions, and `.tmpl` marks Go templates. Keep host-specific logic in templates and shared values in Chezmoi data. Preserve hook ordering and execution semantics encoded in filenames such as `run_before_`, `run_once_`, and numbered `run_` scripts. The validation script checks syntax; it does not enforce a repository-wide formatter.

## Testing Guidelines

Tests use standard-library `unittest`, `test_*.py` files, and `test_*` methods. Add regression coverage for changed behavior using temporary directories and mocked or stubbed external commands. Keep tests isolated from live `/etc`, package managers, services, secrets, and Git remotes. No numeric coverage threshold is configured. Template validation covers the configured host; check rendering and affected host behavior separately for `fi` (desktop), `li` (laptop), and `si` (server). Report skipped rendering explicitly, and distinguish syntax checks from live service validation.

## Commit & Pull Request Guidelines

Use imperative summaries or scoped Conventional Commits such as `fix(nginx): correct redirect`. Keep commits focused and preserve unrelated staged, unstaged, and untracked work. Describe the affected hosts, operational effects, and validation performed.

## Configuration & Secrets

Keep credentials out of committed files and rendered examples. Preserve encryption and private-file attributes, and respect host-specific exclusions in `etc/.chezmoiignore`. Update the relevant operational guide when changing provisioning, recovery, or maintenance workflows. Follow `SERVER-BOOTSTRAP.md` and `SERVER-REBUILD.md` for server work; do not use a blanket apply as a fresh-server recovery procedure. For live system changes, verify the target, preserve a recovery path, and check the affected configuration and services after applying.
