"""Fleet DAG policy, using the existing tjikup runner for presentation/reporting."""
from contextlib import nullcontext
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import tempfile
import textwrap

from .dag import Task, run, command as run_command
from .core import UpdateError
from tjikup import runtime
from .repository_progress import RepositoryProgress
from .presentation import summary


class Stopped(Exception):
    pass


def failure_details(step, output, repo):
    """Keep Git advice out of the status rows without losing diagnostics."""
    dirty = re.search(r"^fleet-update: (Dirty [^\n]+)", output, re.MULTILINE)
    if dirty:
        return [dirty.group(1)], "dirty checkout"
    conflicts = list(dict.fromkeys(re.findall(r"^CONFLICT[^\n]*", output, re.MULTILINE)))
    lines = conflicts or [line for line in output.splitlines()
                          if line.startswith(("fatal:", "error:", "Permission denied"))][:3]
    if not lines and output.strip():
        lines = output.strip().splitlines()[-3:]
    if conflicts and step.get("verb") == "PULL":
        command = step["command"]
        target = (Path(command[command.index("--repo") + 1]).expanduser()
                  if "--repo" in command else repo)
        lines.append(f"Inspect: git -C {shlex.quote(str(target))} status")
        if "could not apply" in output.lower():
            lines.append("After resolving and staging files, continue in that repository:")
            lines.append("git rebase --continue")
    return lines, "merge conflict" if conflicts else "command failed"


def show_failure(step, output, repo, error, seconds, *, status=True):
    lines, reason = failure_details(step, output, repo)
    if not output:
        lines = [str(error)]
    if status:
        runtime.stage_label(step.get("verb", "FAILED"), "✗", step.get("label", step["id"]),
                            f"{reason} · {seconds:.2f}s")
    else:
        print(f'{step.get("label", step["id"])} {step.get("verb", "FAILED")}: {reason}', flush=True)
    if output:
        try:
            state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
            directory = state / "tjikup/logs"
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor, filename = tempfile.mkstemp(prefix=f'{step["id"]}-', suffix=".log", dir=directory)
            with os.fdopen(descriptor, "w") as stream:
                stream.write(output)
            lines.append(f"Log: {filename}")
        except OSError as log_error:
            # Never discard evidence if the state directory is unwritable.
            lines = [f"Could not save log: {log_error}", *output.splitlines()]
    for line in lines:
        print(textwrap.fill(line, width=runtime.terminal_columns() - 1,
                            initial_indent="          ", subsequent_indent="          ",
                            break_long_words=False, break_on_hyphens=False), flush=True)


def workflow(repo, *, dry_run=False):
    plan = json.loads((Path(__file__).with_name("workflow.json")).read_text())
    from .fleet_apply import plans
    plans(repo, Path.home() / ".local/share/chezetc")
    # Lock the complete capture/pull/apply transaction, not just each Git command.
    lock_path = repo / ".git/tjikup-workflow.lock"
    with (nullcontext() if dry_run else lock_path.open("a")) as lock:
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        tasks = []
        outputs = {}
        skipped = set()
        steps = {step["id"]: step for step in plan}
        progress = RepositoryProgress()
        repository_steps = {
            "pull-home": ("dotjik", "PULL"), "push-home": ("dotjik", "PUSH"),
            "pull-system": ("systjik", "PULL"), "push-system": ("systjik", "PUSH"),
            "pull-tooltjik": ("tooltjik", "PULL"), "dirty": ("dotjik", "PUSH"),
        }
        diagnostics = []

        def settle_repositories():
            if dry_run:
                return
            progress.open()
            progress.settle()
            for step, output, result in diagnostics:
                show_failure(step, output, repo, result.error, result.seconds, status=False)
            diagnostics.clear()

        def action(step):
            def execute():
                command = step.get("preview") if dry_run else step["command"]
                if command is None:
                    return
                command = [arg.replace("{config_dir}", str(repo)) for arg in command]
                command = [str(Path(arg).expanduser()) if arg.startswith("~/") else arg for arg in command]
                # Apply owns the terminal; parallel Git operations use private output.
                if step.get("exclusive"):
                    code = runtime.run_stream(command, repo, env=os.environ.copy(),
                                              timeout=step.get("timeout", 300), check=False)
                    output = ""
                else:
                    result = run_command(command, cwd=repo, timeout=step.get("timeout", 300))
                    code, output = result.returncode, result.stdout
                outputs[step["id"]] = output
                if code in step.get("stop_codes", []):
                    raise Stopped(f'{step["id"]}: configuration refresh required')
                if code in step.get("skip_codes", []):
                    skipped.add(step["id"])
                    return
                if code:
                    raise UpdateError(f'{step["id"]}: command failed ({code})')
            return execute

        def event(name, result):
            step = steps[name]
            label, verb = step.get("label", name), step.get("verb", "UPDATE")
            if not dry_run and name in repository_steps:
                repository, operation = repository_steps[name]
                output = outputs.get(name, "")
                if name == "dirty" and result.state != "failed":
                    return
                state = result.state
                if state == "done":
                    outcome = summary(output) if output else None
                    state = "unchanged" if name in skipped else "changed"
                    if name == "pull-tooltjik" and outcome:
                        state = ("changed" if outcome.verb == "PULL" else
                                 "blocked" if outcome.verb == "WARN" or "not cloned" in output else "unchanged")
                        if outcome.warnings:
                            with progress.output():
                                print(output, end="" if output.endswith("\n") else "\n", flush=True)
                    # Tooltjik's command already records its detailed outcome.
                    if name != "pull-tooltjik":
                        runtime.record("SKIP" if state == "unchanged" else operation,
                                       "✓", label, state)
                elif state == "failed":
                    details, reason = failure_details(step, output, repo)
                    note = details[0] if details else str(result.error)
                    runtime.record(operation, "✗", label, note)
                    diagnostics.append((step, output, result))
                progress.update(repository, operation, state)
                return
            if result.state == "running":
                if step.get("exclusive"):
                    settle_repositories()
                with progress.output():
                    if "section" in step:
                        runtime.section_header(step["section"])
                    if "banner" in step:
                        runtime.repo_header(**step["banner"])
                if not dry_run and step.get("summary", True) and not step.get("exclusive"):
                    progress.start(name, label, verb)
                return
            output = outputs.get(name, "")
            if result.state == "failed":
                if name == "commit" and not dry_run:
                    progress.update("dotjik", "PULL", "failed")
                progress.discard(name)
                with progress.output():
                    show_failure(step, output, repo, result.error, result.seconds)
            elif result.state == "blocked":
                if step.get("summary", True) and not step.get("exclusive"):
                    progress.finish(name, f"{verb.title()} {label}", verb="SKIP", icon="-", note="workflow stopped")
            else:
                if output:
                    with progress.output():
                        print(output, end="" if output.endswith("\n") else "\n", flush=True)
                if not dry_run and step.get("summary", True):
                    if name in skipped:
                        progress.finish(name, f"{verb.title()} {label}", verb="SKIP", note="no changes")
                    else:
                        progress.finish(name, label, verb=verb, note=f"{result.seconds:.2f}s")
                if name == "commit" and not dry_run:
                    progress.open()

        for step in plan:
            tasks.append(Task(step["id"], action(step), tuple(step.get("needs", [])),
                              tuple(step.get("resources", [])),
                              check=(lambda: True) if dry_run and "preview" not in step else None,
                              exclusive=step.get("exclusive", False)))
        with progress:
            results = run(tasks, workers=4, event=event)
            settle_repositories()
        errors = [result.error for result in results.values() if result.error]
        if errors:
            if all(isinstance(error, Stopped) for error in errors):
                return 78
            # Each failure has already been rendered with its diagnostics.
            return 1
    return 0
