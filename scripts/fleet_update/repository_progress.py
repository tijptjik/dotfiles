"""Stable fleet repository rows sharing the runner's terminal frame handling."""
from tjikup import runtime
from tjikup.progress import Progress


class RepositoryProgress(Progress):
    repositories = ("dotjik", "systjik", "tjikos")
    colors = {"pending": "90", "disabled": "90", "blocked": "90",
              "running": "1", "changed": "94;1", "unchanged": "36",
              "failed": "31;1"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.states = {repo: {verb: "pending" for verb in ("PULL", "PUSH")}
                       for repo in self.repositories}
        self.visible = False
        self.finished = False

    def line(self, repo):
        cells = self.states[repo]
        name = "tjikOS" if repo == "tjikos" else repo
        if runtime.use_color():
            label = f"{name:<8}"
            if "failed" in cells.values():
                label = f"\033[31;1m{label}\033[0m"
            return label + "  " + "  ".join(
                f"\033[{self.colors[state]}m{verb}\033[0m"
                for verb, state in cells.items())
        if self.live:
            markers = {"pending": "·", "disabled": "-", "blocked": "-",
                       "running": "…", "changed": "↑", "unchanged": "✓", "failed": "✗"}
            return f"{name:<8}  " + "  ".join(
                f"{verb}{markers[state]}" for verb, state in cells.items())
        return f"{name:<8}  " + "  ".join(
            f"{verb} [{state}]" for verb, state in cells.items())

    def _draw(self):
        if self.live and self.visible:
            for repo in self.repositories:
                self.stream.write(self.line(repo) + "\n")
            self.height = len(self.repositories)

    def open(self):
        with self.lock, self._frame():
            if self.visible or self.finished:
                return
            runtime.section_header("Fleet repositories")
            self.visible = True
            # Keep the runner's redraw/cursor lifecycle active for this panel.
            self.rows["repositories"] = ("", "", 0)
            self._draw()

    def update(self, repo, verb, state):
        with self.lock, self._frame():
            self._clear()
            # A failed dirty check and its blocked push share the same cell.
            if self.states[repo][verb] != "failed":
                self.states[repo][verb] = state
            self._draw()

    def settle(self):
        with self.lock, self._frame(active=False):
            if not self.visible:
                return
            self._clear()
            for cells in self.states.values():
                for verb, state in cells.items():
                    if state == "running":
                        cells[verb] = "failed"
            for repo in self.repositories:
                self.stream.write(self.line(repo) + "\n")
            self.rows.clear()
            self.visible = False
            self.finished = True

    def __exit__(self, *args):
        self.settle()
        super().__exit__(*args)
