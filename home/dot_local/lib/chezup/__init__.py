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
GUM = shutil.which("gum")


def run(command: list[str], cwd: Path | None = None, *, capture_output: bool = False) -> None:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=capture_output, check=False)
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
    return propagators


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


def report(message: str) -> None:
    if GUM and sys.stdout.isatty():
        run([GUM, "style", "--foreground", "42", "--bold", message])
    else:
        print(message)


def run_step(title: str, command: list[str], cwd: Path) -> None:
    if GUM and sys.stdout.isatty():
        run([GUM, "spin", "--show-error", "--title", title, "--", *command], cwd)
        report(f"OK   {title}")
    else:
        report(f"RUN  {title}")
        run(command, cwd, capture_output=True)
        report(f"OK   {title}")


def update_chezetc() -> None:
    if not (CHEZETC_REPO / ".git").is_dir():
        raise UpdateError(f"missing chezetc repository: {CHEZETC_REPO}")
    chezetc = shutil.which("chezetc") or str(Path.home() / ".tools/chezetc/chezetc")
    run_step("Rebasing chezetc", ["git", "pull", "--rebase", "--autostash"], CHEZETC_REPO)
    run_step("Applying chezetc", [chezetc, "apply"], CHEZETC_REPO)


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

    if changed_names and not args.quiet:
        report("Updated templates: " + ", ".join(changed_names))
    elif not args.quiet:
        report("Templates already current")

    run_step("Rebasing dotfiles", ["git", "pull", "--rebase", "--autostash"], repo)
    source_paths = [str(propagator.source) for propagator in propagators]
    has_changes = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *source_paths], cwd=repo, check=False).returncode != 0
    if has_changes:
        run_step("Committing dotfiles", ["git", "commit", "--only", "-m", COMMIT_MESSAGE, "--", *source_paths], repo)
    elif not args.quiet:
        report("No propagator changes to commit")
    run_step("Pushing dotfiles", ["git", "push"], repo)
    run_step("Applying chezmoi", ["chezmoi", "apply"], repo)
    update_chezetc()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UpdateError as error:
        print(f"chezup: {error}", file=sys.stderr)
        raise SystemExit(1)
