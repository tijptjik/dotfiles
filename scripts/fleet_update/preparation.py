"""Preparation spinners that yield the terminal to native output and prompts."""
from contextlib import redirect_stdout, redirect_stderr
import sys
import time

from .icons import HookProgress


class PreparationProgress(HookProgress):
    output_open = False

    def _cursor(self, hidden):
        super()._cursor(hidden and not self.output_open)

    def _draw(self):
        if not self.output_open:
            super()._draw()


class PreparationOutput:
    """Clear the active row before output; keep partial prompts unobstructed."""
    def __init__(self, progress, stream):
        self.progress, self.stream = progress, stream

    def write(self, value):
        if not value:
            return 0
        with self.progress.lock, self.progress._frame(active=False):
            self.progress._clear()
            result = self.stream.write(value)
            self.stream.flush()
            self.progress.output_open = not value.endswith('\n')
            self.progress._draw()
            return result

    def __getattr__(self, name):
        return getattr(self.stream, name)


def prepare(label, verb, action, *, exit_code=False):
    """Return the native result and duration, settling one informational row."""
    started = time.monotonic()
    with PreparationProgress() as progress:
        progress.start('preparation', label, verb)
        status, icon = 'FAILED', '✗'
        try:
            with redirect_stdout(PreparationOutput(progress, sys.stdout)), \
                    redirect_stderr(PreparationOutput(progress, sys.stderr)):
                result = action()
            if exit_code and result:
                status, icon = ('WARN', '!') if result == 78 else ('FAILED', '✗')
            else:
                status, icon = verb, '✓'
            return result, time.monotonic() - started
        except KeyboardInterrupt:
            status, icon = 'STOP', '!'
            raise
        finally:
            if progress.output_open:
                progress.stream.write('\n')
                progress.output_open = False
            progress.finish('preparation', label, verb=status, icon=icon,
                            note=f'{time.monotonic() - started:.2f}s', record=False)
