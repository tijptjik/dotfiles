"""One resource-aware graph for home and system hooks; native tools apply files."""
import importlib.util
import os
from pathlib import Path
import tempfile

from .core import UpdateError
from .dag import Task, run, validate, command
from .home_apply import load_plan, render_hook
from .hook_tasks import HookTasks
from tjikup import runtime


def system_policy(repo):
    path = repo / "scripts/tjikup-plan.py"
    if not path.is_file():
        raise UpdateError("System checkout lacks the fleet DAG adapter; update Chezetc before running tjikup")
    spec = importlib.util.spec_from_file_location("fleet_system_plan", path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    if policy.API_VERSION != 1:
        raise UpdateError("Unsupported system DAG adapter version")
    return policy


def plans(repo, system_repo):
    home = load_plan(repo)
    if "chezetc-wrapper" not in {item["id"] for item in home}:
        raise UpdateError("Home plan must provide the Chezetc wrapper prerequisite")
    policy = system_policy(system_repo)
    system = policy.load_plan(system_repo)
    validate([Task(x["id"], None, tuple(x.get("needs", []))) for x in system])
    return home, system, policy


def combine(home_tasks, system_tasks, prepare):
    """File preparation gates system hooks; final network/reboot tasks join both layers."""
    home_names = tuple(task.name for task in home_tasks)
    tasks = [prepare, *home_tasks, *system_tasks]
    for task in system_tasks:
        # System shutdown of fi's tailnet must follow all home networking too.
        if task.name in {"system:tailscale", "system:release"}:
            task.needs += home_names
    validate(tasks)
    return tasks


def apply(repo, system_repo=None):
    from . import apply_files
    system_repo = system_repo or Path.home() / ".local/share/chezetc"
    home_plan, system_plan, policy = plans(repo, system_repo)
    # Validate concurrency settings before any native apply or hook mutation.
    try:
        workers = int(os.environ.get("FLEET_JOBS", "4"))
        if workers < 1:
            raise ValueError()
    except ValueError:
        raise UpdateError("FLEET_JOBS must be a positive integer") from None
    result = apply_files(repo)
    if result:
        return result
    env = os.environ.copy()
    log_root = Path(env.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "tjikup/logs"
    log_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_dir = Path(tempfile.mkdtemp(prefix="apply-", dir=log_root))
    with tempfile.TemporaryDirectory(prefix="tjikup-hooks-") as temporary:
        hooks = HookTasks(temporary, log_dir, env)
        home_tasks = hooks.prepare(repo, home_plan, lambda item: render_hook(repo, item, hooks.env), prefix="home:")
        home_tasks.sort(key=lambda task: task.name != "home:chezetc-wrapper")
        prepared = {}

        def prepare_system():
            runtime.repo_header(title="Systjik", url="https://github.com/tijptjik/systjik")
            # Worker commands have no terminal. Check this exact execution mode
            # before starting system mutations, instead of hanging on a prompt.
            check = command(["sudo", "-n", "true"], cwd=system_repo)
            if check.returncode:
                raise UpdateError("System workers require noninteractive sudo; configure the managed sudo policy first")
            policy.apply_files(system_repo)
            tasks = hooks.prepare(system_repo, system_plan,
                                  lambda item: policy.render_hook(system_repo, item, hooks.env), prefix="system:", root=True)
            prepared.update({task.name: task for task in tasks})

        native = Task("system:files", prepare_system, needs=("home:chezetc-wrapper",), exclusive=True)
        hooks.items[native.name] = {"label": "System files and hook preparation", "verb": "APPLY", "exclusive": True}
        system_tasks = []
        for item in system_plan:
            name = "system:" + item["id"]
            hooks.items[name] = item
            system_tasks.append(Task(name, lambda name=name: prepared[name].run(),
                ("system:files", *("system:" + dep for dep in item.get("needs", []))),
                tuple(item.get("resources", [])), exclusive=item.get("exclusive", False)))
        tasks = combine(home_tasks, system_tasks, native)
        runtime.section_header("Home and system configuration")
        try:
            with hooks.progress:
                results = run(tasks, workers=workers, event=hooks.event)
        finally:
            timing = hooks.save_timings(tasks)
            print(f"Task timings: {timing}", flush=True)
        if any(result.state == "failed" for result in results.values()):
            return 1
    return 0
