"""Home hook inventory and native rendering; scheduling is shared with system work."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .core import UpdateError
from .dag import Task, run, validate
from .hook_tasks import HookTasks
from tjikup import runtime


def load_plan(repo):
    manifest = json.loads(Path(__file__).with_name("home-plan.json").read_text())
    directory = repo / "home/.chezmoiscripts"
    actual = {path.name for path in directory.glob("run_after_*")}
    expected = {item["file"] for item in manifest}
    validate([Task(item["id"], None, tuple(item.get("needs", []))) for item in manifest])
    if actual != expected:
        raise UpdateError("After-hook manifest mismatch; update home-plan.json: " +
                          ", ".join(sorted(actual ^ expected)))
    return manifest


def render_hook(repo, item, env):
    source = repo / "home/.chezmoiscripts" / item["file"]
    if source.suffix != ".tmpl":
        return source.read_text()
    result = subprocess.run(
        ["chezmoi", "--source", str(repo / "home"), "execute-template", "--file", str(source)],
        env=env, capture_output=True, text=True, timeout=60,
    )
    if result.returncode:
        raise UpdateError(f"cannot render {source.name}: {result.stderr}")
    return result.stdout


def apply_hooks(repo, env):
    plan = load_plan(repo)
    log_root = Path(env.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "tjikup/logs"
    log_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_dir = Path(tempfile.mkdtemp(prefix="home-", dir=log_root))
    with tempfile.TemporaryDirectory(prefix="tjikup-hooks-") as temporary:
        hooks = HookTasks(temporary, log_dir, env)
        tasks = hooks.prepare(repo, plan, lambda item: render_hook(repo, item, hooks.env))
        runtime.section_header("Home Configuration")
        try:
            with hooks.progress:
                results = run(tasks, workers=int(os.environ.get("FLEET_JOBS", "4")), event=hooks.event)
        finally:
            hooks.save_timings(tasks)
        failures = [result.error for result in results.values() if result.error]
        if failures:
            raise UpdateError(str(failures[0]))
