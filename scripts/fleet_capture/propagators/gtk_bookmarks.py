"""Capture GTK bookmarks without overwriting another device's list."""

from __future__ import annotations

import json
import socket
from pathlib import Path

from fleet_capture.core import Propagator, UpdateError


class GtkBookmarksPropagator(Propagator):
    name = "gtk-bookmarks"
    order = 60
    optional = True
    source = Path("native/home/data/gtk-bookmarks.json")
    target = Path(".config/gtk-3.0/bookmarks")

    def propagate(
        self, source_path: Path, target_path: Path, output_path: Path
    ) -> None:
        data = json.loads(source_path.read_text())
        bookmarks = data.get("gtkBookmarks")
        if not isinstance(bookmarks, dict) or not all(
            isinstance(host, str) and isinstance(value, str)
            for host, value in bookmarks.items()
        ):
            raise UpdateError("gtkBookmarks must map hostnames to bookmark text")
        # Keep URI escaping, labels, ordering and an intentionally empty list.
        bookmarks[socket.gethostname()] = target_path.read_text()
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )


PROPAGATOR = GtkBookmarksPropagator()
