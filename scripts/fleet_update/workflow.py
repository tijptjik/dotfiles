"""Fleet DAG policy, using the existing tjikup runner for presentation/reporting."""
from contextlib import nullcontext
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

from .dag import Task, run, command as run_command
from .core import UpdateError
from tjikup import runtime


class Stopped(Exception):
    pass


def workflow(repo, *, dry_run=False):
    plan = json.loads((Path(__file__).with_name("workflow.json")).read_text())
    from .home_apply import load_plan
    load_plan(repo)
    # Lock the complete capture/pull/apply transaction, not just each Git command.
    lock_path = repo / ".git/tjikup-workflow.lock"
    with (nullcontext() if dry_run else lock_path.open("a")) as lock:
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        tasks = []
        outputs = {}

        def action(step):
            def execute():
                command = step.get("preview") if dry_run else step["command"]
                if command is None:
                    return
                command = [arg.replace("{config_dir}", str(repo)) for arg in command]
                command = [str(Path(arg).expanduser()) if arg.startswith("~/") else arg for arg in command]
                runtime.section_header(step["section"]) if "section" in step else None
                if "banner" in step:
                    runtime.repo_header(**step["banner"])
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
                    return
                if code:
                    raise UpdateError(f'{step["id"]}: command failed ({code})')
            return execute

        def event(name, result):
            if result.state == "running":
                runtime.stage_started("DAG", name)
                return
            output = outputs.get(name, "")
            if output:
                print(output, end="" if output.endswith("\n") else "\n", flush=True)
            if result.state == "failed":
                runtime.stage_label("FAILED", "✗", name, str(result.error))
            elif result.state == "blocked":
                runtime.stage_skip(name, "prerequisite failed or workflow stopped")
            elif not dry_run:
                runtime.stage_result("DAG", name, f"{result.seconds:.2f}s")

        for step in plan:
            tasks.append(Task(step["id"], action(step), tuple(step.get("needs", [])),
                              tuple(step.get("resources", [])),
                              check=(lambda: True) if dry_run and "preview" not in step else None,
                              exclusive=step.get("exclusive", False)))
        results = run(tasks, workers=4, event=event)
        errors = [result.error for result in results.values() if result.error]
        if errors:
            if all(isinstance(error, Stopped) for error in errors):
                return 78
            raise UpdateError(str(errors[0]))
    return 0
