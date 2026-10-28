"""Fleet-specific capture, Git and home-apply policy for the dotfiles workflow."""

from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import difflib
import fcntl
import importlib
import os
import pkgutil
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from fleet_update.core import Propagator, UpdateError
from tjikup.runtime import (
    run,
    status_msg,
    stage_label,
    stage_result,
    stage_started,
    stage_unchanged,
    stage_expected,
    stage_skip,
    section_header,
    repo_header,
    terminal_columns,
    display_width,
    shorten_status,
)
from tjikup import runtime
from .status import stage_label, stage_result, stage_unchanged, stage_expected, stage_skip

COMMAND_TIMEOUT_SECONDS = 300
CHEZMOI_CONFIG_WARNING = "chezmoi: warning: config file template has changed, run chezmoi init to regenerate config file"


def discover_propagators() -> list[Propagator]:
    package_name = "fleet_update.propagators"
    package = importlib.import_module(package_name)
    propagators: list[Propagator] = []
    for module_info in sorted(
        pkgutil.iter_modules(package.__path__), key=lambda item: item.name
    ):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{package_name}.{module_info.name}")
        propagator = getattr(module, "PROPAGATOR", None)
        if not isinstance(propagator, Propagator):
            raise UpdateError(f"{module_info.name} must export a PROPAGATOR instance")
        propagators.append(propagator)
    if not propagators:
        raise UpdateError("no propagators found")
    return sorted(
        propagators,
        key=lambda propagator: (getattr(propagator, "order", 100), propagator.name),
    )


def show_diff(path: Path, before: str, after: str) -> None:
    sys.stdout.writelines(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


@contextmanager
def apply_conflict_policy(command: list[str], skip_conflicts: bool):
    """Feed chezmoi's per-conflict skip response without requiring a TTY."""
    if not skip_conflicts:
        yield (command, None)
        return
    with subprocess.Popen(["yes", "skip"], stdout=subprocess.PIPE) as answers:
        try:
            yield ([*command, "--no-tty", "--interactive=false"], answers.stdout)
        finally:
            answers.stdout.close()
            answers.terminate()
            answers.wait()


def run_chezmoi_apply(
    repo: Path, command: list[str], env: dict[str, str], *, skip_conflicts: bool = False
) -> bool:
    if sys.stdout.isatty() or os.environ.get("TJIKUP_COLOR") == "1":
        saw_warning = False

        def format_line(line):
            nonlocal saw_warning
            if CHEZMOI_CONFIG_WARNING in line:
                saw_warning = True
            return format_apply_output(line)

        try:
            run_stream(
                command,
                repo,
                env=env,
                skip_conflicts=skip_conflicts,
                formatter=format_line,
            )
        except UpdateError:
            stage_label("FAILED", "✗", "Dotfiles apply")
            raise
        if saw_warning:
            stage_label("WARN", "!", "Chezmoi config changed; run chezmoi init")
        return not saw_warning
    try:
        with apply_conflict_policy(command, skip_conflicts) as (apply_command, stdin):
            result = subprocess.run(
                apply_command,
                cwd=repo,
                env=env,
                stdin=stdin,
                text=True,
                capture_output=True,
                check=False,
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
    except subprocess.TimeoutExpired as error:
        stage_label("FAILED", "✗", "Dotfiles apply")
        raise UpdateError(
            f"command timed out after {COMMAND_TIMEOUT_SECONDS}s: {' '.join(command)}"
        ) from error
    except OSError as error:
        raise UpdateError(f"could not run {' '.join(command)}: {error}") from error
    output = (result.stdout or "") + (result.stderr or "")
    if CHEZMOI_CONFIG_WARNING in output:
        remaining = output.replace(CHEZMOI_CONFIG_WARNING, "").strip()
        if remaining:
            print(remaining)
        stage_label("WARN", "!", "Chezmoi config changed; run chezmoi init")
        if result.returncode:
            stage_label("FAILED", "✗", "Dotfiles apply")
            raise UpdateError(
                f"command failed ({result.returncode}): {' '.join(command)}"
            )
        return False
    if result.stdout:
        sys.stdout.write(
            "\n".join((format_apply_output(line) for line in result.stdout.split("\n")))
        )
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode:
        stage_label("FAILED", "✗", "Dotfiles apply")
        raise UpdateError(f"command failed ({result.returncode}): {' '.join(command)}")
    return True


def format_apply_output(line: str) -> str:
    """Give common chezmoi apply change messages the same shape as status rows."""
    from .status import decorate_native_row
    removed = re.fullmatch("Removed '(.+)'\\.", line)
    if removed:
        return _apply_status_row("REMOVE", "✓", removed.group(1))
    symlink = re.fullmatch("Created symlink '(.+)' -> '(.+)'\\.", line)
    if symlink:
        return _apply_status_row(
            "LINK", "✓", f"{symlink.group(1)} → {symlink.group(2)}"
        )
    return decorate_native_row(line)


def _apply_status_row(verb: str, icon: str, subject: str) -> str:
    prefix = f"{verb:<7} {icon} "
    available = max(1, terminal_columns() - 1 - display_width(prefix))
    subject = shorten_status(subject, available)
    if not sys.stdout.isatty():
        return prefix + subject
    verb_color = "31;1" if verb == "REMOVE" else "36;1"
    return f"\x1b[{verb_color}m{verb:<7}\x1b[0m \x1b[32m{icon}\x1b[0m {subject}"


def run_checks(repo: Path) -> None:
    grouped_checks = [
        (
            "Bitwarden",
            [
                ("Secrets Manager CLI", shutil.which("bws") is not None),
                ("Access Token", (Path.home() / ".config/bws/environment").is_file()),
            ],
        ),
        (
            "Chezmoi",
            [
                ("Decryption Key", (Path.home() / ".keys/chezmoi.txt").is_file()),
                ("Chezetc TOML modules", has_python_modules("tomli", "tomli_w")),
            ],
        ),
    ]
    command_checks = [
        ("Fish", shutil.which("fish") is not None),
        ("UV", shutil.which("uv") is not None),
        ("FNM", shutil.which("fnm") is not None),
        ("Gum", shutil.which("gum") is not None),
        ("Bun", shutil.which("bun") is not None),
    ]
    for subject, requirements in grouped_checks:
        missing = [name for name, available in requirements if not available]
        if missing:
            stage_label("CHECK", "!", subject, f"missing: {', '.join(missing)}")
        else:
            stage_result("CHECK", subject, "available")
    for subject, available in command_checks:
        if available:
            stage_result("CHECK", subject, "available")
        else:
            stage_skip(subject)


def git_ref(repo: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return None
    return result.stdout.strip()


def git_dirty_paths(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise UpdateError(f"cannot determine dirty status: {repo}")
    return [line[3:] for line in result.stdout.splitlines() if len(line) >= 4]


def warn_dirty_files(status_repo: Path, repo: Path) -> None:
    paths = git_dirty_paths(repo)
    if paths:
        count = len(paths)
        name = repo.resolve().name
        name = {"chezmoi": "Dotjik", "chezetc": "Systjik"}.get(name, name)
        raise UpdateError(f"{name} has changes - commit or stash them first "
                          f"({count} {('file' if count == 1 else 'files')})")


def changed_line_count(before: str, after: str) -> int:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines)
    changes = sum(
        (
            i2 - i1 + (j2 - j1)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes()
            if tag != "equal"
        )
    )
    return changes or 1


def elapsed_note(seconds: float) -> str:
    return f"{seconds:.2f}s"


def propagate_one(
    propagator: Propagator, source: Path, target: Path, output: Path
) -> tuple[str, str, float]:
    started = time.perf_counter()
    before = source.read_text()
    propagator.propagate(source, target, output)
    after = output.read_text()
    return (before, after, time.perf_counter() - started)


def backup_live_output(propagator: Propagator, output: Path) -> None:
    """Keep the captured live bytes before updating a source; never run on dry-run."""
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    directory = state / "tjikup/backups" / propagator.name
    directory.mkdir(parents=True, exist_ok=True, mode=448)
    prefix = time.strftime("%Y%m%dT%H%M%SZ-", time.gmtime())
    descriptor, name = tempfile.mkstemp(prefix=prefix, suffix=".backup", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(output.read_bytes())
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def changed_propagator_names(repo: Path, propagators: list[Propagator]) -> list[str]:
    paths = [str(propagator.source) for propagator in propagators]
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", *paths],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    changed_paths = set(result.stdout.splitlines()) if result.returncode == 0 else set()
    return [
        propagator.name
        for propagator in propagators
        if str(propagator.source) in changed_paths
    ]


def commit_templates(
    status_repo: Path, repo: Path, propagators: list[Propagator]
) -> list[str]:
    changed_names = changed_propagator_names(repo, propagators)
    if not changed_names:
        stage_unchanged("Local Changes")
        return []
    changed_paths = [
        str(propagator.source)
        for propagator in propagators
        if propagator.name in changed_names
    ]
    stage_started("COMMIT", "Templates")
    started = time.perf_counter()
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
        stage_label("FAILED", "✗", "Templates")
        raise
    stage_result(
        "COMMIT",
        "Templates",
        f"{len(changed_names)} files · {elapsed_note(time.perf_counter() - started)}",
    )
    return changed_names


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


def has_python_modules(*modules: str) -> bool:
    python = shutil.which("python3")
    if python is None:
        return False
    result = subprocess.run(
        [python, "-c", "; ".join((f"import {module}" for module in modules))],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def capture(repo: Path, *, dry_run: bool = False) -> int:
    propagators = discover_propagators()
    resolved = [
        (propagator, repo / propagator.source, Path.home() / propagator.target)
        for propagator in propagators
    ]
    active_propagators: list[Propagator] = []
    active_resolved: list[tuple[Propagator, Path, Path]] = []
    for propagator, source, target in resolved:
        if not source.is_file():
            raise UpdateError(f"{propagator.name}: missing chezmoi template: {source}")
        if not target.is_file():
            if propagator.optional:
                stage_expected(propagator.name.capitalize(), "not installed")
                continue
            raise UpdateError(f"{propagator.name}: missing live config: {target}")
        active_propagators.append(propagator)
        active_resolved.append((propagator, source, target))
    with tempfile.TemporaryDirectory(prefix="tjikup-") as temp_dir:
        temp = Path(temp_dir)
        changed_names: list[str] = []
        sync_changes: dict[str, int] = {}
        sync_elapsed: dict[str, float] = {}
        pending_writes: list[tuple[Path, str]] = []
        failures = False
        with ThreadPoolExecutor(
            max_workers=min(4, max(1, len(active_resolved))),
            thread_name_prefix="tjikup-sync",
        ) as pool:
            futures = [
                pool.submit(
                    propagate_one,
                    propagator,
                    source,
                    target,
                    temp / f"{propagator.name}.template",
                )
                for propagator, source, target in active_resolved
            ]
            for (propagator, source, _), future in zip(active_resolved, futures):
                try:
                    before, after, seconds = future.result()
                except UpdateError as error:
                    stage_label("SYNC", "✗", propagator.name.capitalize(), str(error))
                    failures = True
                    continue
                sync_elapsed[propagator.name] = seconds
                if before == after:
                    continue
                changed_names.append(propagator.name)
                sync_changes[propagator.name] = changed_line_count(before, after)
                if dry_run:
                    show_diff(source, before, after)
                else:
                    pending_writes.append((source, after))
        if failures:
            return 1
        if not dry_run:
            for propagator in active_propagators:
                if propagator.backup_live:
                    backup_live_output(propagator, temp / f"{propagator.name}.template")
        for source, after in pending_writes:
            source.write_text(after)
    for propagator in active_propagators:
        if propagator.name in changed_names:
            changes = sync_changes[propagator.name]
            stage_result(
                "SYNC",
                propagator.name.capitalize(),
                f"{changes} changes · {elapsed_note(sync_elapsed[propagator.name])}",
            )
        else:
            stage_unchanged(
                propagator.name.capitalize(),
                f"no changes · {elapsed_note(sync_elapsed[propagator.name])}",
            )
    return 0


def run_stream(
    command,
    cwd,
    *,
    env=None,
    timeout=COMMAND_TIMEOUT_SECONDS,
    skip_conflicts=False,
    formatter=None,
):
    from .preparation import PreparationOutput
    stderr_handler = sys.stderr.write if isinstance(sys.stderr, PreparationOutput) else None
    with apply_conflict_policy(command, skip_conflicts) as (command, stdin):
        return runtime.run_stream(
            command,
            cwd,
            env=env,
            timeout=timeout,
            stdin=stdin,
            formatter=formatter or format_apply_output,
            stderr_handler=stderr_handler,
        )


def sync_repo(repo, action):
    if not (repo / ".git").exists():
        raise UpdateError(f"missing repository: {repo}")
    # A second tjikup can otherwise fetch and advance refs while the first is
    # rebasing this same worktree. Git then aborts with "Cannot rebase onto
    # multiple branches". The lock is per repository, so home and system
    # repositories still synchronize concurrently.
    with (repo / ".git" / "tjikup-sync.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            warn_dirty_files(repo, repo)
            if action == "pull":
                before = git_ref(repo, "HEAD")
                if before is None:
                    raise UpdateError(f"cannot determine HEAD: {repo}")
                run(["git", "pull", "--rebase", "--no-autostash"], repo, capture_output=True)
                after = git_ref(repo, "HEAD")
                if after is None:
                    raise UpdateError(f"cannot determine pull result: {repo}")
                if before == after:
                    return 77
            elif action == "push":
                ahead = git_ahead_count(repo)
                if ahead is None:
                    raise UpdateError(f"cannot determine upstream status: {repo}")
                if not ahead:
                    return 77
                run(["git", "push"], repo, capture_output=True)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["check", "capture", "commit", "dirty", "pull", "push", "pull-tjikos", "push-tjikos", "apply", "workflow"],
    )
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.dry_run and args.action not in {"capture", "workflow", "pull-tjikos", "push-tjikos"}:
        parser.error("--dry-run is supported only by capture, workflow, pull-tjikos and push-tjikos")
    if args.action == "pull-tjikos":
        from .tjikos_sync import pull
        return pull(dry_run=args.dry_run)
    if args.action == "push-tjikos":
        from .tjikos_sync import push
        return push(dry_run=args.dry_run)
    if args.action == "workflow":
        from .workflow import workflow
        return workflow(repo, dry_run=args.dry_run)
    if args.action == "check":
        system_repo = Path.home() / ".local/share/chezetc"
        for required in (
            repo / ".git",
            system_repo / ".git",
            system_repo / "scripts/tjikup-apply.py",
        ):
            if not required.exists():
                raise UpdateError(f"missing fleet dependency: {required}")
        run_checks(repo)
    elif args.action == "capture":
        return capture(repo, dry_run=args.dry_run)
    elif args.action == "commit":
        active = [
            p for p in discover_propagators() if (Path.home() / p.target).is_file()
        ]
        if not commit_templates(repo, repo, active):
            return 77
    elif args.action == "dirty":
        warn_dirty_files(repo, repo)
    elif args.action in {"pull", "push"}:
        return sync_repo(repo, args.action)
    elif args.action == "apply":
        from .fleet_apply import apply
        return apply(repo)
    return 0


def apply_files(repo):
    """Leave native file, once and onchange handling with Chezmoi."""
    from .home_apply import load_plan
    load_plan(repo)
    if chezmoi_config_needs_init(repo):
        stage_label("WARN", "!", "Chezmoi config changed; run chezmoi init")
        return 78
    env = {**os.environ, "CHEZMOI_SKIP_SPLASH": "1", "TJIKUP_SKIP_PREFLIGHT": "1",
           "FLEET_DEFER_HOOKS": "1"}
    # Bind apply explicitly to the source selected by the workflow.
    if not run_chezmoi_apply(
        repo,
        ["chezmoi", "--source", str(repo / "home"), "apply"],
        env,
        skip_conflicts=os.environ.get("FLEET_SKIP_CONFLICTS") == "1",
    ):
        return 78
    return 0
