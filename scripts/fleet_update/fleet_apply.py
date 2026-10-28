"""One resource-aware graph for home and system hooks; native tools apply files."""
import importlib.util
from dataclasses import replace
from itertools import zip_longest
import os
from pathlib import Path
import tempfile
import time

from .core import UpdateError
from .dag import Result, Task, run, validate, command
from .home_apply import load_plan, render_hook
from .hook_tasks import HookTasks
from .preparation import prepare
from .presentation import DeferredSection, timing_report


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
    system_repo = system_repo or Path.home() / ".local/share/systjik"
    home_plan, system_plan, policy = plans(repo, system_repo)
    # Validate concurrency settings before any native apply or hook mutation.
    try:
        workers = int(os.environ.get("FLEET_JOBS", "4"))
        if workers < 1:
            raise ValueError()
    except ValueError:
        raise UpdateError("FLEET_JOBS must be a positive integer") from None
    started = time.monotonic()
    env = os.environ.copy()
    log_root = Path(env.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "tjikup/logs"
    with tempfile.TemporaryDirectory(prefix="tjikup-hooks-") as temporary:
        # Keep file application and hook preparation under one Chezmoi row.
        # Do not create hook workers/state when native apply requests an init.
        home_tasks = []
        home_file_seconds = home_render_seconds = 0

        def prepare_home():
            nonlocal hooks, home_tasks, home_file_seconds, home_render_seconds, log_dir
            file_started = time.monotonic()
            result = apply_files(repo)
            home_file_seconds = time.monotonic() - file_started
            if result:
                return result
            log_root.mkdir(parents=True, exist_ok=True, mode=0o700)
            log_dir = Path(tempfile.mkdtemp(prefix="apply-", dir=log_root))
            hooks = HookTasks(temporary, log_dir, env)
            render_started = time.monotonic()
            home_tasks = hooks.prepare(
                repo, home_plan, lambda item: render_hook(repo, item, hooks.env), prefix="home:")
            home_render_seconds = time.monotonic() - render_started
            return 0

        hooks = None
        log_dir = None
        result, _ = prepare("Chezmoi (home directory)", "CHECK", prepare_home, exit_code=True)
        if result:
            return result
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
        hooks.items[native.name] = {"label": "Chezetc (system)", "verb": "CHECK", "exclusive": True}
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
        preparation_names = {"home:chezetc-wrapper", "system:files"}
        preparation_tasks = [task for task in tasks if task.name in preparation_names]
        remaining_tasks = [replace(task, needs=tuple(
            name for name in task.needs if name not in preparation_names))
            for task in tasks if task.name not in preparation_names]

        def run_phase(phase, *, preparation=False):
            offset = time.monotonic() - started

            def event(name, result):
                # Both phases share the timing receipt's apply-relative clock.
                if result.started is not None:
                    result.started += offset
                    result.finished += offset
                if preparation:
                    if result.state != "running":
                        hooks.results[name] = result
                else:
                    hooks.event(name, result)

            return run(phase, workers=workers, event=event)

        def prepare_chezetc():
            results = run_phase(preparation_tasks, preparation=True)
            for name, result in results.items():
                if result.state == "failed":
                    hooks.results.update({task.name: Result("blocked") for task in remaining_tasks})
                    output = hooks.outputs.get(name, "")
                    if output:
                        print(output, end="" if output.endswith("\n") else "\n", flush=True)
                        print(f"Log: {hooks.log_dir / (name.replace(':', '-') + '.log')}", flush=True)
                    raise UpdateError(str(result.error))

        try:
            prepare("Chezetc (system)", "CHECK", prepare_chezetc)
            hooks.progress.section = DeferredSection("Home + System Tasks")
            with hooks.progress:
                results = run_phase(remaining_tasks)
                if all(result.state in {"done", "skipped"} for result in results.values()):
                    hooks.progress.finish_empty_section()
        finally:
            timing = hooks.save_timings(tasks, total_seconds=time.monotonic() - started,
                                       home_file_seconds=home_file_seconds, home_render_seconds=home_render_seconds)
            receipt = os.environ.get("FLEET_TIMING_RECEIPT")
            if receipt:
                Path(receipt).write_text(str(timing))
            else:
                timing_report(timing)
        if any(result.state == "failed" for result in results.values()):
            return 1
    return 0
