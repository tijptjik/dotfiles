"""Application-specific capture recipe; independent of the tjikup runtime."""
from concurrent.futures import ThreadPoolExecutor
import difflib
import importlib
import os
from pathlib import Path
import pkgutil
import sys
import tempfile
import time
from .core import Propagator, UpdateError


def stage_label(verb, icon, subject, note=""):
    # Keep identity separate from the status, for both native reports and the
    # standalone stdout protocol. Timings must never become part of an app name.
    verb, icon, subject, note = (
        str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")
        for value in (verb, icon, subject, note)
    )
    if report := os.environ.get("TJIKUP_REPORT_FILE"):
        descriptor = os.open(report, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"{verb}\t{icon}\t{subject}\t{note}\n")
    print(f"{verb:<7} {icon} {subject}  {note}", flush=True)


def stage_result(verb, subject, note=""):
    stage_label(verb, "✓", subject, note)


def stage_unchanged(subject, note=""):
    stage_label("SKIP", "✓", subject, note)


def stage_expected(subject, note=""):
    stage_label("SKIP", "-", subject, note)


def discover_propagators() -> list[Propagator]:
    package_name = "fleet_capture.propagators"
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
            raise UpdateError(f"{propagator.name}: missing native template: {source}")
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
