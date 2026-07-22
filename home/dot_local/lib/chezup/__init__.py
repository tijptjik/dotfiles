"""Extensible chezmoi live-state propagation workflow."""

from __future__ import annotations

import argparse
import difflib
import importlib
import os
import pkgutil
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from chezup.core import Propagator, UpdateError


COMMIT_MESSAGE = "fix: latest zed and herdr"
CHEZETC_REPO = Path.home() / ".local/share/chezetc"


def run(
    command: list[str],
    cwd: Path | None = None,
    *,
    capture_output: bool = False,
    env: dict[str, str] | None = None,
) -> None:
    try:
        result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=capture_output, check=False)
    except OSError as error:
        raise UpdateError(f"could not run {' '.join(command)}: {error}") from error
    if result.returncode:
        if capture_output:
            output = (result.stdout or "") + (result.stderr or "")
            if output:
                print(output, file=sys.stderr, end="")
        raise UpdateError(f"command failed ({result.returncode}): {' '.join(command)}")


def discover_propagators() -> list[Propagator]:
    package_name = "chezup.propagators"
    package = importlib.import_module(package_name)
    propagators: list[Propagator] = []
    for module_info in sorted(pkgutil.iter_modules(package.__path__), key=lambda item: item.name):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{package_name}.{module_info.name}")
        propagator = getattr(module, "PROPAGATOR", None)
        if not isinstance(propagator, Propagator):
            raise UpdateError(f"{module_info.name} must export a PROPAGATOR instance")
        propagators.append(propagator)
    if not propagators:
        raise UpdateError("no propagators found")
    return sorted(propagators, key=lambda propagator: (getattr(propagator, "order", 100), propagator.name))


def find_repo() -> Path:
    configured = os.environ.get("CHEZUP_REPO") or os.environ.get("CHEZUPDATE_REPO")
    if configured:
        return Path(configured).expanduser().resolve()
    fallback = Path.home() / ".local/share/chezmoi"
    try:
        result = subprocess.run(["chezmoi", "source-path"], text=True, capture_output=True, timeout=10, check=False)
        candidate = Path(result.stdout.strip()).expanduser().resolve()
        if result.returncode == 0 and (candidate / ".git").exists():
            return candidate
    except (OSError, subprocess.TimeoutExpired):
        pass
    return fallback


def show_diff(path: Path, before: str, after: str) -> None:
    sys.stdout.writelines(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def stage_label(repo: Path, verb: str, icon: str, subject: str) -> None:
    helper = repo / "home/.chezmoihelpers/status.fish"
    fish = shutil.which("fish")
    if fish and helper.is_file() and sys.stdout.isatty():
        result = subprocess.run(
            [
                fish,
                "-c",
                'source $argv[1]; __stage_label $argv[2] $argv[3] $argv[4]',
                "--",
                str(helper),
                verb,
                icon,
                subject,
            ],
            check=False,
        )
        if result.returncode == 0:
            return
    print(f"{verb:<7} {icon} {subject}")


def stage_result(repo: Path, verb: str, subject: str) -> None:
    stage_label(repo, verb, "✓", subject)


def stage_skip(repo: Path, subject: str) -> None:
    stage_label(repo, "SKIP", "-", subject)


def run_stage(repo: Path, verb: str, subject: str, command: list[str], cwd: Path) -> None:
    try:
        run(command, cwd, capture_output=True)
    except UpdateError:
        stage_label(repo, "FAILED", "✗", subject)
        raise
    stage_result(repo, verb, subject)


def run_stream(command: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> None:
    try:
        result = subprocess.run(command, cwd=cwd, env=env, check=False)
    except OSError as error:
        raise UpdateError(f"could not run {' '.join(command)}: {error}") from error
    if result.returncode:
        raise UpdateError(f"command failed ({result.returncode}): {' '.join(command)}")


def print_header(repo: Path) -> None:
    run_stream(["bash", str(repo / "home/.chezmoiscripts/run_before_00-print-header.sh")], repo)


def run_checks(repo: Path) -> None:
    checks = [
        ("Bitwarden Secrets Manager CLI", shutil.which("bws") is not None),
        ("Bitwarden Access Token", (Path.home() / ".config/bws/environment").is_file()),
        ("Chezmoi Decryption Key", (Path.home() / ".keys/chezmoi.txt").is_file()),
        ("Gum", shutil.which("gum") is not None),
        ("Fish", shutil.which("fish") is not None),
        ("Bun", shutil.which("bun") is not None),
        ("FNM", shutil.which("fnm") is not None),
        ("Herdr", shutil.which("herdr") is not None),
    ]
    for subject, available in checks:
        if available:
            stage_result(repo, "CHECK", subject)
        else:
            stage_skip(repo, subject)


def update_chezetc(status_repo: Path) -> None:
    if not (CHEZETC_REPO / ".git").is_dir():
        raise UpdateError(f"missing chezetc repository: {CHEZETC_REPO}")
    chezetc = shutil.which("chezetc") or str(Path.home() / ".tools/chezetc/chezetc")
    run_stage(status_repo, "UPDATE", "Chezetc", ["git", "pull", "--rebase", "--autostash"], CHEZETC_REPO)
    run_stream([chezetc, "apply"], CHEZETC_REPO)


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--dry-run", action="store_true", help="show template changes without git or chezmoi mutations")
    arguments.add_argument("--quiet", action="store_true", help="suppress unchanged-file and diff output")
    args = arguments.parse_args()

    repo = find_repo()
    if not args.quiet:
        print_header(repo)
        run_checks(repo)
    propagators = discover_propagators()
    resolved = [(propagator, repo / propagator.source, Path.home() / propagator.target) for propagator in propagators]
    for propagator, source, target in resolved:
        if not source.is_file():
            raise UpdateError(f"{propagator.name}: missing chezmoi template: {source}")
        if not target.is_file():
            raise UpdateError(f"{propagator.name}: missing live config: {target}")

    with tempfile.TemporaryDirectory(prefix="chezup-") as temp_dir:
        temp = Path(temp_dir)
        changed_names: list[str] = []
        for propagator, source, target in resolved:
            before = source.read_text()
            output = temp / f"{propagator.name}.template"
            propagator.propagate(source, target, output)
            after = output.read_text()
            if before != after:
                changed_names.append(propagator.name)
                if args.dry_run and not args.quiet:
                    show_diff(source, before, after)
            elif args.dry_run and not args.quiet:
                print(f"unchanged: {propagator.name}")
            if not args.dry_run:
                source.write_text(after)

    if args.dry_run:
        print("dry-run complete")
        return 0

    for propagator in propagators:
        if propagator.name in changed_names:
            stage_result(repo, "SYNC", propagator.name.capitalize())
        elif not args.quiet:
            stage_skip(repo, propagator.name.capitalize())

    run_stage(repo, "UPDATE", "Chezmoi", ["git", "pull", "--rebase", "--autostash"], repo)
    source_paths = [str(propagator.source) for propagator in propagators]
    has_changes = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *source_paths], cwd=repo, check=False).returncode != 0
    if has_changes:
        run_stage(repo, "COMMIT", "Templates", ["git", "commit", "--only", "-m", COMMIT_MESSAGE, "--", *source_paths], repo)
        run_stage(repo, "PUSH", "Dotfiles", ["git", "push"], repo)
    else:
        stage_skip(repo, "Templates")
        stage_skip(repo, "Dotfiles")
    if changed_names:
        auto_targets = [
            str(Path.home() / propagator.target)
            for propagator in propagators
            if propagator.name in changed_names
        ]
        run_stream(
            ["chezmoi", "apply", "--force", *auto_targets],
            repo,
            env={**os.environ, "CHEZMOI_SKIP_SPLASH": "1", "CHEZUP_SKIP_PREFLIGHT": "1"},
        )
    run_stream(
        ["chezmoi", "apply"],
        repo,
        env={**os.environ, "CHEZMOI_SKIP_SPLASH": "1", "CHEZUP_SKIP_PREFLIGHT": "1"},
    )
    update_chezetc(repo)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UpdateError as error:
        print(f"chezup: {error}", file=sys.stderr)
        raise SystemExit(1)
