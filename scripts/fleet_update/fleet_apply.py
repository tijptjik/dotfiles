"""One resource-aware graph for home and system hooks; native tools apply files."""
import importlib.util
from itertools import zip_longest
import os
from pathlib import Path
import tempfile
import time

from .core import UpdateError
from .dag import Task, run, validate, command
from .home_apply import load_plan, render_hook
from .hook_tasks import HookTasks
from .preparation import prepare
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
    # Check cross-layer barriers before native file application as well.
    combine([Task("home:" + x["id"], None, tuple("home:" + n for n in x.get("needs", []))) for x in home],
            [Task("system:" + x["id"], None, ("system:files", *("system:" + n for n in x.get("needs", [])))) for x in system],
            Task("system:files", None, ("home:chezetc-wrapper",)),
            {**{"home:" + x["id"]: x.get("barrier") for x in home},
             **{"system:" + x["id"]: x.get("barrier") for x in system}})
    return home, system, policy


def combine(home_tasks, system_tasks, prepare, barriers=None):
    """File preparation gates system hooks; final network/reboot tasks join both layers."""
    home_names = tuple(task.name for task in home_tasks)
    # Alternate layers so a long list of ready home hooks cannot postpone the
    # system package prerequisite chain until the end (or vice versa).
    tasks = [prepare, *(task for pair in zip_longest(system_tasks, home_tasks) for task in pair if task)]
    for task in (*home_tasks, *system_tasks):
        # Final network policy and release checks follow home networking too.
        barrier = (barriers or {}).get(task.name)
        if barrier == "updates-final":
            # Runtime refresh must follow every installer, including system
            # packages. Network/release barriers already depend on home tasks.
            task.needs = tuple(dict.fromkeys((*task.needs, *(
                other.name for other in tasks if other is not task
                and (barriers or {}).get(other.name) not in {"network-final", "final"}
            ))))
        elif barrier == "network-final":
            task.needs += home_names
        elif barrier == "final":
            task.needs = tuple(other.name for other in tasks if other is not task)
        elif barrier is not None:
            raise UpdateError(f"Unknown task barrier: {barrier}")
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
    started = time.monotonic()
    result, home_file_seconds = prepare("Chezmoi files", "APPLY", lambda: apply_files(repo), exit_code=True)
    if result:
        return result
    env = os.environ.copy()
    log_root = Path(env.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "tjikup/logs"
    log_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_dir = Path(tempfile.mkdtemp(prefix="apply-", dir=log_root))
    with tempfile.TemporaryDirectory(prefix="tjikup-hooks-") as temporary:
        hooks = HookTasks(temporary, log_dir, env)
        home_tasks, home_render_seconds = prepare("Home hooks", "RENDER", lambda: hooks.prepare(
            repo, home_plan, lambda item: render_hook(repo, item, hooks.env), prefix="home:"))
        home_tasks.sort(key=lambda task: task.name != "home:chezetc-wrapper")
        prepared = {}

        def prepare_system():
            # Worker commands have no terminal. Check this exact execution mode
            # before starting system mutations, instead of hanging on a prompt.
            check = command(["sudo", "-n", "true"], cwd=system_repo)
            if check.returncode:
                raise UpdateError("System workers require noninteractive sudo; configure the managed sudo policy first")
            policy.apply_files(system_repo)
            rendered = policy.render_hooks(system_repo, system_plan, hooks.env)
            tasks = hooks.prepare(system_repo, system_plan,
                                  lambda item: rendered[item["file"]], prefix="system:", root=True)
            prepared.update({task.name: task for task in tasks})

        native = Task("system:files", prepare_system, needs=("home:chezetc-wrapper",), exclusive=True)
        hooks.items[native.name] = {"label": "Chezetc (files and hooks)", "verb": "APPLY", "exclusive": True}
        system_tasks = []
        for item in system_plan:
            name = "system:" + item["id"]
            hooks.items[name] = item
            system_tasks.append(Task(name, lambda name=name: prepared[name].run(),
                ("system:files", *("system:" + dep for dep in item.get("needs", []))),
                tuple(item.get("resources", [])),
                check=lambda name=name: prepared[name].check is not None and prepared[name].check(),
                exclusive=lambda name=name: (prepared[name].exclusive() if callable(prepared[name].exclusive)
                                              else prepared[name].exclusive)))
        tasks = combine(home_tasks, system_tasks, native,
                        {**{"home:" + item["id"]: item.get("barrier") for item in home_plan},
                         **{"system:" + item["id"]: item.get("barrier") for item in system_plan}})
        runtime.repo_header(title="Systjik", url="https://github.com/tijptjik/systjik")
        runtime.section_header("Home and system configuration")
        try:
            with hooks.progress:
                results = run(tasks, workers=workers, event=hooks.event)
        finally:
            timing = hooks.save_timings(tasks, total_seconds=time.monotonic() - started,
                                       home_file_seconds=home_file_seconds, home_render_seconds=home_render_seconds)
            print(f"Task timings: {timing}", flush=True)
        if any(result.state == "failed" for result in results.values()):
            return 1
    return 0
