"""Visible preparation phases without taking cursor or terminal input ownership."""
import sys
import threading
import time

from tjikup import runtime
from tjikup.progress import enabled


def prepare(label, verb, action, *, exit_code=False, interval=5.0):
    """Return the action's result and duration; keep native prompts/output intact.

    Append-only heartbeats cannot erase output written directly by Chezmoi to
    stderr. These informational rows do not add stages to the outcome report.
    """
    stream = sys.stdout
    started = time.monotonic()
    stopped = threading.Event()

    def show(status, icon, note):
        stream.write(runtime.format_status(status, icon, label, note) + "\n")
        stream.flush()

    def heartbeat():
        while not stopped.wait(interval):
            show(verb, "…", f"{time.monotonic() - started:.0f}s elapsed")

    show(verb, "…", "starting")
    thread = threading.Thread(target=heartbeat, daemon=True) if enabled() else None
    if thread:
        thread.start()
    status, icon = "FAILED", "✗"
    try:
        result = action()
        if exit_code and result:
            status, icon = ("WARN", "!") if result == 78 else ("FAILED", "✗")
        else:
            status, icon = verb, "✓"
        return result, time.monotonic() - started
    except KeyboardInterrupt:
        status, icon = "STOP", "!"
        raise
    finally:
        stopped.set()
        if thread:
            thread.join()
        show(status, icon, f"{time.monotonic() - started:.2f}s")
