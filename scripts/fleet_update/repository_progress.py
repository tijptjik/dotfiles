"""Stable fleet repository rows sharing the runner's terminal frame handling."""
import math

from tjikup import runtime
from tjikup.progress import Progress
from .icons import title_icon, icons_enabled
from .kitty_icons import KittyIcons
from .presentation import ANSI


class RepositoryProgress(Progress):
    repositories = ("dotjik", "systjik", "tjikos")
    colors = {"pending": "90", "disabled": "90", "blocked": "90",
              "skipped": "90", "running": "1", "changed": "94;1", "unchanged": "36",
              "failed": "31;1"}
    markers = {"skipped": "-", "changed": "✓", "unchanged": "-", "failed": "✗"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.states = {repo: {verb: "pending" for verb in ("PULL", "PUSH")}
                       for repo in self.repositories}
        self.visible = False
        self.finished = False
        self.notes = {}
        self.counts = {}
        self.graphics = KittyIcons.available(self.stream, self.live)

    def print_repository(self, repo):
        prefix = ""
        if self.graphics:
            icon_width = 2 * math.ceil(32 / (2 * self.graphics.geometry[0])) + 1
        else:
            prefix = f"{title_icon(repo)} " if icons_enabled(self.stream, self.live) else ""
            icon_width = len(prefix)
        row = self.line(repo)
        if runtime.display_width(ANSI.sub('', row)) + icon_width >= runtime.terminal_columns():
            row = self.line(repo, compact=True)
        counts = " ".join(
            f"{arrow}{self.counts[repo, verb]}"
            for verb, arrow in (("PULL", "↓"), ("PUSH", "↑"))
            if (repo, verb) in self.counts)
        details = " · ".join(filter(None, (self.notes.get(repo), counts)))
        if details:
            width = runtime.terminal_columns() - 1 - icon_width
            used = runtime.display_width(ANSI.sub('', row))
            available = width - used - 2
            if available > 0:
                note = runtime.shorten_status(details, available)
                padding = ' ' * (width - used - runtime.display_width(note))
                if runtime.use_color():
                    color = '31' if self.notes.get(repo) else '90'
                    note = f'\033[{color}m{note}\033[0m'
                row += padding + note
        if self.graphics:
            self.graphics.print_text(repo, row)
        else:
            self.stream.write(prefix + row + "\n")

    def line(self, repo, *, compact=False):
        cells = self.states[repo]
        name = "tjikOS" if repo == "tjikos" else repo
        label = f"{name:<{6 if compact else 8}}"
        gap, marker_gap = (" ", "") if compact else ("  ", " ")
        if runtime.use_color():
            if "failed" in cells.values():
                label = f"\033[31;1m{label}\033[0m"
            return label + gap + " ".join(
                f"\033[{self.colors[state]}m{self.markers.get(state, ' ')}{marker_gap}{verb}\033[0m"
                for verb, state in cells.items())
        if self.live:
            return label + gap + " ".join(
                f"{self.markers.get(state, ' ')}{marker_gap}{verb}" for verb, state in cells.items())
        return f"{name:<8}  " + "  ".join(
            f"{verb} [{state}]" for verb, state in cells.items())

    def _draw(self):
        if self.live and self.visible:
            for repo in self.repositories:
                self.print_repository(repo)
            self.height = len(self.repositories) * (2 if self.graphics else 1)

    def open(self):
        with self.lock, self._frame():
            if self.visible or self.finished:
                return
            if self.live:
                runtime.section_header("Repos")
            self.visible = True
            # Keep the runner's redraw/cursor lifecycle active for this panel.
            self.rows["repositories"] = ("", "", 0)
            self._draw()

    def update(self, repo, verb, state, *, note=None, count=None):
        with self.lock, self._frame():
            self._clear()
            # A failed dirty check and its blocked push share the same cell.
            if self.states[repo][verb] != "failed":
                self.states[repo][verb] = state
                if count is not None:
                    self.counts[repo, verb] = count
                else:
                    self.counts.pop((repo, verb), None)
            if note is not None:
                self.notes[repo] = note
            self._draw()

    def settle(self):
        with self.lock, self._frame(active=False):
            if not self.visible:
                return
            self._clear()
            if not self.live:
                runtime.section_header("Repos")
            for cells in self.states.values():
                for verb, state in cells.items():
                    if state == "running":
                        cells[verb] = "failed"
            for repo in self.repositories:
                self.print_repository(repo)
            self.rows.clear()
            self.visible = False
            self.finished = True

    def __exit__(self, *args):
        self.settle()
        super().__exit__(*args)
