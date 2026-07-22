"""Extensible chezmoi live-state propagation workflow."""

from __future__ import annotations

import argparse
import difflib
import importlib
import os
import pkgutil
import subprocess
import sys
import tempfile
from pathlib import Path

from chezupdate.core import Propagator, UpdateError


COMMIT_MESSAGE = "fix: latest zed and herdr"


def run(command: list[str], cwd: Path | None = None) -> None:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, check=False)
    except OSError as error:
        raise UpdateError(f"could not run {' '.join(command)}: {error}") from error
    if result.returncode:
        raise UpdateError(f"command failed ({result.returncode}): {' '.join(command)}")


def discover_propagators() -> list[Propagator]:
    package_name = "chezupdate.propagators"
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
    return propagators


def find_repo() -> Path:
    configured = os.environ.get("CHEZUPDATE_REPO")
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


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--dry-run", action="store_true", help="show template changes without git or chezmoi mutations")
    arguments.add_argument("--quiet", action="store_true", help="suppress unchanged-file and diff output")
    args = arguments.parse_args()

    repo = find_repo()
    propagators = discover_propagators()
    resolved = [(propagator, repo / propagator.source, Path.home() / propagator.target) for propagator in propagators]
    for propagator, source, target in resolved:
        if not source.is_file():
            raise UpdateError(f"{propagator.name}: missing chezmoi template: {source}")
        if not target.is_file():
            raise UpdateError(f"{propagator.name}: missing live config: {target}")

    with tempfile.TemporaryDirectory(prefix="chezupdate-") as temp_dir:
        temp = Path(temp_dir)
        for propagator, source, target in resolved:
            before = source.read_text()
            output = temp / f"{propagator.name}.template"
            propagator.propagate(source, target, output)
            after = output.read_text()
            if before != after:
                if not args.quiet:
                    show_diff(source, before, after)
            elif not args.quiet:
                print(f"unchanged: {source}")
            if not args.dry_run:
                source.write_text(after)

    if args.dry_run:
        print("dry-run complete")
        return 0

    run(["git", "pull", "--rebase", "--autostash"], repo)
    source_paths = [str(propagator.source) for propagator in propagators]
    has_changes = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *source_paths], cwd=repo, check=False).returncode != 0
    if has_changes:
        run(["git", "commit", "--only", "-m", COMMIT_MESSAGE, "--", *source_paths], repo)
    elif not args.quiet:
        print("no propagator changes to commit")
    run(["git", "push"], repo)
    run(["chezmoi", "apply"], repo)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UpdateError as error:
        print(f"chezupdate: {error}", file=sys.stderr)
        raise SystemExit(1)
