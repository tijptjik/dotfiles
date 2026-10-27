"""Capture the generated desktop MIME cache before Chezmoi applies it."""

from pathlib import Path

from fleet_update.core import Propagator, UpdateError


class MimeinfoPropagator(Propagator):
    name = "mimeinfo"
    order = 70
    optional = True
    source = Path("home/dot_local/share/applications/mimeinfo.cache")
    target = Path(".local/share/applications/mimeinfo.cache")

    def propagate(
        self, source_path: Path, target_path: Path, output_path: Path
    ) -> None:
        live = target_path.read_text()
        if not live.startswith("[MIME Cache]\n"):
            raise UpdateError("mimeinfo.cache is missing its [MIME Cache] header")
        output_path.write_text(live)


PROPAGATOR = MimeinfoPropagator()
