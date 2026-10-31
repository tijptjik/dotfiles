"""Columnar archive output using tjikup's terminal palette and section headings."""

import contextlib
import os
from pathlib import Path
import shutil
import sys
import textwrap
import threading
import time
import unicodedata


def clean(value):
    return "".join(
        "?" if unicodedata.category(c).startswith("C") else c for c in str(value)
    )


def cells(value):
    return sum(
        0
        if unicodedata.combining(c)
        else 2
        if unicodedata.east_asian_width(c) in ("W", "F")
        else 1
        for c in value
    )


def clip(value, width, middle=False):
    value = clean(value)
    if cells(value) <= width:
        return value
    if width <= 1:
        return "…"[: max(0, width)]
    left_width = (width - 1) // 2 if middle else width - 1
    left = ""
    for char in value:
        if cells(left + char) > left_width:
            break
        left += char
    if not middle:
        return left + "…"
    right = ""
    for char in reversed(value):
        if cells(char + right) > width - 1 - cells(left):
            break
        right = char + right
    return left + "…" + right


def field(value, width, right=False, middle=False):
    value = clip(value, width, middle)
    padding = " " * max(0, width - cells(value))
    return padding + value if right else value + padding


def size_label(size):
    if size is None:
        return "—"
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024


class Feedback:
    def __init__(self, repo=None, columns=None):
        self.repo = Path(repo or Path.home() / "code/dotjik")
        self.terminal = sys.stdout.isatty()
        self.color = (
            self.terminal or os.environ.get("TJIKUP_COLOR") == "1"
        ) and "NO_COLOR" not in os.environ
        self.width = max(
            23, (columns or shutil.get_terminal_size((120, 24)).columns) - 1
        )
        self.lock = threading.Lock()
        self.phase, self.subject, self.note = "CHECK", "", ""
        self.skipped = False
        self.entries = self.size = None
        self.index, self.count = 1, 1
        self.started = time.monotonic()
        self.active_lines = 0

    def paint(self, text, code):
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def header(self, machine, count):
        self.count = count
        title = f"Device Archives [{machine} · {count} {'folder' if count == 1 else 'folders'}]"
        print("\n" + self.paint(title, "94;1") + "\n", flush=True)
        print(
            self.paint(
                self.line(
                    "STATUS",
                    "",
                    "FOLDER",
                    "ENTRIES",
                    "SIZE",
                    "RESULT",
                    "TIME",
                    heading=True,
                ),
                "90",
            ),
            flush=True,
        )

    def line(self, verb, icon, subject, entries, size, result, elapsed, heading=False):
        digits = len(str(self.count))
        item = (
            field("ITEM", max(4, digits * 2 + 1))
            if heading
            else field(f"{self.index:>{digits}}/{self.count}", max(4, digits * 2 + 1))
        )
        prefix = f"{field(verb, 8)} {icon or ' '} {item} "
        tail = "  ".join(
            (
                field(entries, 7, True),
                field(size, 10, True),
                field(result, 9),
                field(elapsed, 8, True),
            )
        )
        available = self.width - cells(prefix) - cells(tail) - 2
        if available >= 12:
            return prefix + field(subject, available, middle=True) + "  " + tail
        # Small terminals retain full numeric columns on a separate line.
        first = prefix + field(subject, max(1, self.width - cells(prefix)), middle=True)
        if self.width >= cells(tail) + 2:
            second = "  " + tail
        else:
            second = "  " + field(entries, 7, True) + "  " + field(size, 10, True)
            second += "\n  " + field(result, 9) + "  " + field(elapsed, 8, True)
        return first + "\n" + second

    def _clear(self):
        if self.active_lines:
            sys.stdout.write("\r\033[2K")
            for _ in range(self.active_lines - 1):
                sys.stdout.write("\033[1A\r\033[2K")
            self.active_lines = 0

    def _write(self, line, verb, icon, transient=False, columnar=True):
        self._clear()
        # Apply colours only after measuring/padding the plain text.
        first, *following = line.split("\n")
        folder_start = 12 + max(4, len(str(self.count)) * 2 + 1)
        folder_end = len(first) if following else max(folder_start, len(first) - 42)
        if columnar:
            rest = (
                self.paint(first[10:folder_start], "90")
                + self.paint(first[folder_start:folder_end], "97")
                + self.paint(first[folder_end:], "90")
            )
        else:
            rest = self.paint(first[10:], "97")
        line = (
            self.paint(first[:8], "91;1" if verb in ("FAILED", "ABORT") else "96;1")
            + first[8:9]
            + self.paint(
                first[9:10], "92" if icon == "✓" else "91" if icon == "✗" else "93"
            )
            + rest
        )
        if following:
            line += "\n" + self.paint("\n".join(following), "90")
        sys.stdout.write(line)
        if transient and self.terminal:
            self.active_lines = line.count("\n") + 1
        else:
            sys.stdout.write("\n")
        sys.stdout.flush()

    def row(self, verb, icon, subject, note=""):
        self._clear()
        # Run summaries have their own line and cannot shift the folder columns.
        line = f"{field(verb, 8)} {icon} {clean(subject)}  {clean(note)}"
        for part in textwrap.wrap(
            line, width=self.width, subsequent_indent="           "
        ):
            self._write(part, verb, icon, columnar=False)

    def _result(self, verb, icon, result, transient=False):
        elapsed = time.monotonic() - self.started
        duration = f"{elapsed:.1f}s" if elapsed < 100000 else f"{elapsed / 3600:.1f}h"
        entries = (
            "—"
            if self.entries is None
            else f"{self.entries:,}"
            if self.entries < 1000000
            else f"{self.entries / 1000000:.1f}M"
        )
        self._write(
            self.line(
                verb,
                icon,
                self.subject,
                entries,
                size_label(self.size),
                result,
                duration,
            ),
            verb,
            icon,
            transient,
        )

    def _render(self):
        result = (
            "readback"
            if self.note.startswith("download ")
            else "hashing"
            if self.note.startswith("compare content")
            else "running"
        )
        self._result(self.phase, "…", result, transient=True)

    def event(self, phase, folder, note=""):
        with self.lock:
            if phase in ("METRICS", "DONE", "SKIP"):
                self.entries = note.get("entries", self.entries)
                self.size = note.get("size", self.size)
                if phase != "METRICS":
                    self.skipped = phase == "SKIP"
                return
            self.phase, self.note = phase, note
            self._render()

    @contextlib.contextmanager
    def folder(self, folder, index, count):
        self.subject, self.index, self.count = folder, index, count
        self.started = time.monotonic()
        self.skipped = False
        self.entries = self.size = None
        stop = threading.Event()

        def heartbeat():
            while not stop.wait(5 if self.terminal else 30):
                with self.lock:
                    self._render()

        worker = threading.Thread(target=heartbeat, daemon=True)
        worker.start()
        try:
            yield
        except BaseException as error:
            stop.set()
            worker.join()
            interrupted = isinstance(error, KeyboardInterrupt)
            self._result(
                "ABORT" if interrupted else "FAILED",
                "!" if interrupted else "✗",
                "stopped" if interrupted else "failed",
            )
            if not interrupted:
                for line in textwrap.wrap(clean(error), width=max(1, self.width - 2)):
                    print("  " + line, flush=True)
            raise
        else:
            stop.set()
            worker.join()
            self._result(
                "SKIP" if self.skipped else "BACKUP",
                "✓",
                "unchanged" if self.skipped else "verified",
            )
        finally:
            stop.set()
            worker.join()
