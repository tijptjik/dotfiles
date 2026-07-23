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

from tjikup.core import Propagator, UpdateError


CHEZETC_REPO = Path.home() / ".local/share/chezetc"
GUM = shutil.which("gum")
CHEZMOI_CONFIG_WARNING = "chezmoi: warning: config file template has changed, run chezmoi init to regenerate config file"


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
    package_name = "tjikup.propagators"
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
    configured = os.environ.get("TJIKUP_REPO") or os.environ.get("TJIKUPDATE_REPO")
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


def stage_label(repo: Path, verb: str, icon: str, subject: str, note: str | None = None) -> None:
    if note:
        note = note.strip()
        if note.startswith("(") and note.endswith(")"):
            note = note[1:-1]
    helper = repo / "home/.chezmoihelpers/status.fish"
    fish = shutil.which("fish")
    if fish and helper.is_file() and sys.stdout.isatty():
        function = "__stage_label_note" if note else "__stage_label"
        arguments = [verb, icon, subject] + ([note] if note else [])
        result = subprocess.run(
            [
                fish,
                "-c",
                f"source $argv[1]; {function} $argv[2] $argv[3] $argv[4]" + (" $argv[5]" if note else ""),
                "--",
                str(helper),
                *arguments,
            ],
            check=False,
        )
        if result.returncode == 0:
            return
    if note:
        prefix_length = 10
        note_column = 72
        padding = max(2, note_column - prefix_length - len(subject) - len(note))
        print(f"{verb:<7} {icon} {subject}{' ' * padding}{note}")
    else:
        print(f"{verb:<7} {icon} {subject}")


def stage_result(repo: Path, verb: str, subject: str, note: str | None = None) -> None:
    stage_label(repo, verb, "✓", subject, note)


def stage_skip(repo: Path, subject: str, note: str | None = None) -> None:
    stage_label(repo, "SKIP", "-", subject, note)


def stage_skip_ok(repo: Path, subject: str, note: str | None = None) -> None:
    stage_label(repo, "SKIP", "✓", subject, note)


def run_stage(
    repo: Path,
    verb: str,
    subject: str,
    command: list[str],
    cwd: Path,
    note: str | None = None,
) -> None:
    try:
        run(command, cwd, capture_output=True)
    except UpdateError:
        stage_label(repo, "FAILED", "✗", subject)
        raise
    stage_result(repo, verb, subject, note)


def section(title: str, *, leading: bool = True) -> None:
    if leading:
        print()
    if GUM and sys.stdout.isatty():
        run([GUM, "style", "--foreground", "12", "--bold", title])
    else:
        print(title)
    print()


def run_stream(command: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> None:
    try:
        result = subprocess.run(command, cwd=cwd, env=env, check=False)
    except OSError as error:
        raise UpdateError(f"could not run {' '.join(command)}: {error}") from error
    if result.returncode:
        raise UpdateError(f"command failed ({result.returncode}): {' '.join(command)}")


def run_chezmoi_apply(repo: Path, command: list[str], env: dict[str, str]) -> bool:
    if sys.stdout.isatty():
        run_stream(command, repo, env=env)
        return True

    try:
        result = subprocess.run(command, cwd=repo, env=env, text=True, capture_output=True, check=False)
    except OSError as error:
        raise UpdateError(f"could not run {' '.join(command)}: {error}") from error

    output = (result.stdout or "") + (result.stderr or "")
    if CHEZMOI_CONFIG_WARNING in output:
        remaining = output.replace(CHEZMOI_CONFIG_WARNING, "").strip()
        if remaining:
            print(remaining)
        stage_label(repo, "WARN", "!", "Chezmoi config changed; run chezmoi init")
        return False

    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode:
        raise UpdateError(f"command failed ({result.returncode}): {' '.join(command)}")
    return True


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
    optional_checks = {"Bitwarden Access Token", "Chezmoi Decryption Key"}
    for subject, available in checks:
        if available:
            stage_result(repo, "CHECK", subject, "available")
        elif subject in optional_checks:
            stage_skip_ok(repo, subject, "not configured")
        else:
            stage_skip(repo, subject)


def git_ref(repo: Path, ref: str) -> str | None:
    result = subprocess.run(["git", "rev-parse", "--verify", ref], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode:
        return None
    return result.stdout.strip()


def git_changed_file_count(repo: Path, before: str | None, after: str | None) -> int:
    if not before or not after or before == after:
        return 0
    result = subprocess.run(["git", "diff", "--name-only", before, after], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode:
        return 0
    return len({line for line in result.stdout.splitlines() if line})


def git_dirty_paths(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return []
    return [line[3:] for line in result.stdout.splitlines() if len(line) >= 4]


def warn_dirty_files(status_repo: Path, repo: Path) -> None:
    paths = git_dirty_paths(repo)
    if paths:
        stage_label(status_repo, "WARN", "!", f"{len(paths)} Dirty Files", "unchanged")


def changed_line_count(before: str, after: str) -> int:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines)
    changes = sum((i2 - i1) + (j2 - j1) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal")
    return changes or 1


def pull_dotfiles(repo: Path) -> None:
    before = git_ref(repo, "HEAD")
    try:
        run(["git", "pull", "--rebase", "--autostash"], repo, capture_output=True)
    except UpdateError:
        stage_label(repo, "FAILED", "✗", "Chezmoi")
        raise
    after = git_ref(repo, "HEAD")
    note = "rebases" if before and after and before != after else "no changes"
    stage_result(repo, "PULL", "Chezmoi", note)


def changed_propagator_names(repo: Path, propagators: list[Propagator]) -> list[str]:
    paths = [str(propagator.source) for propagator in propagators]
    result = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *paths], cwd=repo, text=True, capture_output=True, check=False)
    changed_paths = set(result.stdout.splitlines()) if result.returncode == 0 else set()
    return [propagator.name for propagator in propagators if str(propagator.source) in changed_paths]


def commit_templates(status_repo: Path, repo: Path, propagators: list[Propagator]) -> list[str]:
    changed_names = changed_propagator_names(repo, propagators)
    if not changed_names:
        stage_skip_ok(status_repo, "Templates", "no changes")
        return []

    changed_paths = [
        str(propagator.source)
        for propagator in propagators
        if propagator.name in changed_names
    ]
    try:
        run(["git", "add", "--", *changed_paths], repo, capture_output=True)
        run(
            [
                "git",
                "commit",
                "--only",
                "-m",
                "sync: update templates",
                "--",
                *changed_paths,
            ],
            repo,
            capture_output=True,
        )
    except UpdateError:
        stage_label(status_repo, "FAILED", "✗", "Templates")
        raise
    stage_result(status_repo, "COMMIT", "Templates", f"{len(changed_names)} files")
    return changed_names


def pull_chezetc(status_repo: Path) -> None:
    if not (CHEZETC_REPO / ".git").is_dir():
        raise UpdateError(f"missing chezetc repository: {CHEZETC_REPO}")
    before = git_ref(CHEZETC_REPO, "HEAD")
    run(["git", "pull", "--rebase", "--autostash"], CHEZETC_REPO, capture_output=True)
    after = git_ref(CHEZETC_REPO, "HEAD")
    note = "rebases" if before and after and before != after else "no changes"
    stage_result(status_repo, "PULL", "Chezetc", note)


def git_ahead_count(repo: Path) -> int | None:
    result = subprocess.run(
        ["git", "rev-list", "--count", "@{u}..HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def chezmoi_config_needs_init(repo: Path) -> bool:
    source = repo / "home/.chezmoi.toml.tmpl"
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    target = config_root / "chezmoi/chezmoi.toml"
    if not source.is_file() or not target.is_file():
        return False
    try:
        result = subprocess.run(
            ["chezmoi", "execute-template"],
            cwd=repo,
            input=source.read_text(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout != target.read_text()


def push_committed_chezetc(status_repo: Path) -> None:
    ahead = git_ahead_count(CHEZETC_REPO)
    if not ahead:
        stage_skip_ok(status_repo, "Chezetc", "no local commits")
        return
    run_stage(status_repo, "PUSH", "Chezetc", ["git", "push"], CHEZETC_REPO, "pushed")


def apply_chezetc() -> None:
    chezetc = shutil.which("chezetc") or str(Path.home() / ".tools/chezetc/chezetc")
    run_stream([chezetc, "apply"], CHEZETC_REPO)


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--dry-run", action="store_true", help="show template changes without git or chezmoi mutations")
    args = arguments.parse_args()

    repo = find_repo()
    print_header(repo)
    section("Prerequisites", leading=False)
    run_checks(repo)
    section("Template Sync")
    propagators = discover_propagators()
    resolved = [(propagator, repo / propagator.source, Path.home() / propagator.target) for propagator in propagators]
    for propagator, source, target in resolved:
        if not source.is_file():
            raise UpdateError(f"{propagator.name}: missing chezmoi template: {source}")
        if not target.is_file():
            raise UpdateError(f"{propagator.name}: missing live config: {target}")

    with tempfile.TemporaryDirectory(prefix="tjikup-") as temp_dir:
        temp = Path(temp_dir)
        changed_names: list[str] = []
        sync_changes: dict[str, int] = {}
        for propagator, source, target in resolved:
            before = source.read_text()
            output = temp / f"{propagator.name}.template"
            propagator.propagate(source, target, output)
            after = output.read_text()
            if before != after:
                changed_names.append(propagator.name)
                sync_changes[propagator.name] = changed_line_count(before, after)
                if args.dry_run:
                    show_diff(source, before, after)
            if not args.dry_run:
                source.write_text(after)

    if args.dry_run:
        for propagator in propagators:
            if propagator.name in changed_names:
                changes = sync_changes[propagator.name]
                stage_result(repo, "SYNC", propagator.name.capitalize(), f"{changes} changes")
            else:
                stage_skip_ok(repo, propagator.name.capitalize(), "no changes")
        print("dry-run complete")
        return 0

    for propagator in propagators:
        if propagator.name in changed_names:
            changes = sync_changes[propagator.name]
            stage_result(repo, "SYNC", propagator.name.capitalize(), f"{changes} changes")
        else:
            stage_skip_ok(repo, propagator.name.capitalize(), "no changes")
    section("Git")

    changed_names = commit_templates(repo, repo, propagators)
    pull_dotfiles(repo)
    warn_dirty_files(repo, repo)
    ahead = git_ahead_count(repo)
    if ahead:
        run_stage(repo, "PUSH", "Dotfiles", ["git", "push"], repo, f"{ahead} commits pushed")
    else:
        stage_skip_ok(repo, "Dotfiles", "no changes")
    if chezmoi_config_needs_init(repo):
        stage_label(repo, "WARN", "!", "Chezmoi config changed; run chezmoi init")
        return 0
    if changed_names:
        auto_targets = [
            str(Path.home() / propagator.target)
            for propagator in propagators
            if propagator.name in changed_names
        ]
        if not run_chezmoi_apply(
            repo,
            ["chezmoi", "apply", "--force", *auto_targets],
            {**os.environ, "CHEZMOI_SKIP_SPLASH": "1", "TJIKUP_SKIP_PREFLIGHT": "1"},
        ):
            return 0
    if not run_chezmoi_apply(
        repo,
        ["chezmoi", "apply"],
        {**os.environ, "CHEZMOI_SKIP_SPLASH": "1", "TJIKUP_SKIP_PREFLIGHT": "1"},
    ):
        return 0
    pull_chezetc(repo)
    push_committed_chezetc(repo)
    apply_chezetc()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UpdateError as error:
        print(f"tjikup: {error}", file=sys.stderr)
        raise SystemExit(1)
