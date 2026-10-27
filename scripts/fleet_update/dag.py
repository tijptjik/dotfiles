"""Bounded dependency scheduler. Callbacks own checks and mutations, never the graph."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
import threading
import os
import signal
import subprocess
import time


@dataclass
class Task:
    name: str
    run: object
    needs: tuple = ()
    resources: tuple = ()
    check: object = None
    exclusive: bool = False


@dataclass
class Result:
    state: str
    seconds: float = 0
    error: object = None
    dependency_wait: float = 0
    resource_wait: float = 0
    worker_wait: float = 0
    started: float | None = None
    finished: float | None = None


def validate(tasks):
    nodes = {task.name: task for task in tasks}
    if len(nodes) != len(tasks):
        raise ValueError("duplicate task id")
    remaining = {name: set(task.needs) for name, task in nodes.items()}
    for name, deps in remaining.items():
        if deps - nodes.keys():
            raise ValueError(f"{name}: unknown dependencies {sorted(deps - nodes.keys())}")
    visited = set()
    while remaining:
        ready = {name for name, deps in remaining.items() if deps <= visited}
        if not ready:
            raise ValueError("dependency cycle: " + ", ".join(sorted(remaining)))
        visited.update(ready)
        for name in ready:
            del remaining[name]
    return nodes


def run(tasks, *, workers=4, event=lambda *_: None):
    """Checks run after dependencies and under the same resource lease as writes.

    Stop scheduling on any failure; drain already-running work before returning.
    A skipped prerequisite is satisfied, a failed prerequisite never is.
    Exclusive tasks own the terminal and run alone on the calling thread.
    """
    nodes = validate(tasks)
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be a positive integer")
    pending = dict(nodes)
    results, running = {}, {}
    held = set()
    failed = False
    epoch = time.monotonic()
    waits = {name: dict(dependency_wait=0., resource_wait=0., worker_wait=0.) for name in nodes}
    reasons = {name: "dependency_wait" for name in nodes}
    last_tick = epoch

    def account():
        nonlocal last_tick
        now = time.monotonic()
        for name in pending:
            waits[name][reasons[name]] += now - last_tick
        last_tick = now

    def exclusive(task):
        return task.exclusive() if callable(task.exclusive) else task.exclusive

    def execute(task):
        started = time.monotonic()
        try:
            if task.check is not None and task.check():
                result = Result("skipped")
            else:
                task.run()
                result = Result("done")
        except Exception as error:
            result = Result("failed", error=error)
        finished = time.monotonic()
        result.seconds = finished - started
        result.started, result.finished = started - epoch, finished - epoch
        return result

    def complete(task, result):
        nonlocal failed
        held.difference_update(task.resources)
        for key, value in waits[task.name].items():
            setattr(result, key, value)
        results[task.name] = result
        failed = failed or result.state == "failed"
        event(task.name, result)

    _CANCELLED.clear()
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="apply") as pool:
        try:
            while pending or running:
                account()
                if not failed:
                    for name, task in list(pending.items()):
                        if len(running) >= workers:
                            break
                        if not set(task.needs) <= results.keys() or held.intersection(task.resources):
                            continue
                        if exclusive(task):
                            if running:
                                continue
                            del pending[name]
                            event(name, Result("running"))
                            complete(task, execute(task))
                            account()
                            break
                        held.update(task.resources)
                        del pending[name]
                        event(name, Result("running"))
                        running[pool.submit(execute, task)] = task
                # Attribute queue time to its current limiting condition. The
                # next completion wakes us; no polling or timing-based ordering.
                for name, task in pending.items():
                    if not set(task.needs) <= results.keys():
                        reasons[name] = "dependency_wait"
                    elif held.intersection(task.resources) or (exclusive(task) and running):
                        reasons[name] = "resource_wait"
                    else:
                        reasons[name] = "worker_wait"
                if running:
                    completed, _ = wait(running, return_when=FIRST_COMPLETED)
                    account()
                    for future in completed:
                        complete(running.pop(future), future.result())
                elif failed:
                    break
                elif pending and not any(set(t.needs) <= results.keys() for t in pending.values()):
                    raise RuntimeError("scheduler made no progress")
        except BaseException:
            cancel_commands()
            raise
        for name in pending:
            results[name] = Result("blocked", **waits[name])
            event(name, results[name])
    return results


_CHILDREN = set()
_CHILDREN_LOCK = threading.Lock()
_CANCELLED = threading.Event()


def cancel_commands():
    _CANCELLED.set()
    with _CHILDREN_LOCK:
        for process in _CHILDREN:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def command(argv, *, cwd, env=None, timeout=300):
    """Buffered parallel command with a process-group deadline and cancellation."""
    with _CHILDREN_LOCK:
        if _CANCELLED.is_set():
            raise RuntimeError("workflow cancelled")
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, errors="replace", start_new_session=True)
        _CHILDREN.add(process)
    try:
        output, _ = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(argv, process.returncode, output)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise
    finally:
        with _CHILDREN_LOCK:
            _CHILDREN.discard(process)
