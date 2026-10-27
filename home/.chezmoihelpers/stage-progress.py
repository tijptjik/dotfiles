#!/usr/bin/env python3
"""Run Gum on a private terminal and keep its probes away from shell input."""
import os
import errno
import fcntl
import pty
import shutil
import signal
import struct
import subprocess
import termios
import tty
from pathlib import Path
import re
import sys
import time


PROGRESS = re.compile(
    r'(?:remote: )?((?:Receiving objects|Resolving deltas|Updating files|'
    r'Compressing objects|Counting objects):\s+\d+%[^\r\n]*)'
)


def transfer_progress(path):
    # Bound work even when a build produces a large log; never display arbitrary
    # command output (which may include secrets or terminal control sequences).
    with path.open('rb') as stream:
        stream.seek(0, 2)
        stream.seek(max(0, stream.tell() - 8192))
        tail = stream.read().decode('utf-8', errors='replace')
    matches = PROGRESS.findall(tail)
    if not matches:
        return ''
    detail = re.sub(r'[^a-zA-Z0-9 %(),./|:-]', '', matches[-1]).strip()
    detail = re.sub(r'\s*\(\d+/\d+\)', '', detail)
    return detail.replace('Receiving objects:', 'Download:')


def watch(log, status, pid):
    """Feed only transfer metrics to Gum; the actual command keeps its stdin."""
    started = time.monotonic()
    previous = None
    while not status.stat().st_size:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        detail = transfer_progress(log)
        note = f"{int(time.monotonic() - started)}s"
        if detail:
            note += f" | {detail}"
        if note != previous:
            print(note, end='\r', flush=True)
            previous = note
        time.sleep(.2)


class TerminalRelay:
    """Answer Gum's terminal queries privately; relay display operations only."""

    def __init__(self, master):
        self.master = master
        self.pending = b''

    def feed(self, data):
        self.pending += data
        output = bytearray()
        while self.pending:
            if self.pending[0] != 27:
                end = self.pending.find(b'\x1b')
                if end < 0:
                    end = len(self.pending)
                output.extend(self.pending[:end])
                self.pending = self.pending[end:]
                continue
            if len(self.pending) < 2:
                break
            if self.pending.startswith(b'\x1b['):
                match = re.match(rb'\x1b\[[0-?]*[ -/]*[@-~]', self.pending)
                if not match:
                    break
                token = match[0]
                self.pending = self.pending[len(token):]
                mode = re.fullmatch(rb'\x1b\[\?(\d+)\$p', token)
                if mode:
                    os.write(self.master, b'\x1b[?' + mode[1] + b';0$y')
                elif token == b'\x1b[?u':
                    os.write(self.master, b'\x1b[?0u')
                elif token == b'\x1b[6n':
                    os.write(self.master, b'\x1b[1;1R')
                elif re.fullmatch(rb'\x1b\[[0-9;]*[mABCDEFGHJKSTf]', token):
                    output.extend(token)
                # Keyboard protocols, mode changes and other queries stay here.
            elif self.pending.startswith(b'\x1b]'):
                match = re.match(rb'\x1b\](.*?)(?:\x07|\x1b\\)', self.pending, re.S)
                if not match:
                    break
                self.pending = self.pending[len(match[0]):]
                if match[1] in (b'10;?', b'11;?'):
                    color = b'ffff/ffff/ffff' if match[1].startswith(b'10') else b'0000/0000/0000'
                    os.write(self.master, b'\x1b]' + match[1][:2] + b';rgb:' + color + b'\x1b\\')
            else:
                self.pending = self.pending[2:]
        return bytes(output)


def main():
    if sys.argv[1] == '--watch':
        watch(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]))
        return
    log, status, pid, title = sys.argv[1:5]
    master, slave = pty.openpty()
    columns = shutil.get_terminal_size((80, 24)).columns
    try:
        columns = max(24, int(os.environ.get('TJIKUP_COLUMNS') or
                              os.environ.get('COLUMNS') or columns))
    except ValueError:
        pass
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, columns, 0, 0))
    tty.setraw(slave)  # Never echo capability replies back into the display.
    process = None
    try:
        process = subprocess.Popen([
            'gum', 'spin', '--spinner', 'dot', '--title', title, '--show-output',
            '--', sys.executable, str(Path(__file__).resolve()), '--watch', log, status, pid,
        ], stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
            env={**os.environ, 'TERM': 'xterm-256color'})
        os.close(slave)
        slave = None
        relay = TerminalRelay(master)
        while True:
            try:
                data = os.read(master, 65536)
            except OSError as error:
                if error.errno == errno.EIO:
                    break
                raise
            if not data:
                break
            sys.stdout.buffer.write(relay.feed(data))
            sys.stdout.buffer.flush()
        process.wait()
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        os.close(master)
        if slave is not None:
            os.close(slave)
        sys.stdout.buffer.write(b'\r\x1b[2K')
        sys.stdout.buffer.flush()


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
