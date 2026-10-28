"""Propagate Codex's configuration into the native source tree."""

from __future__ import annotations

from pathlib import Path

from fleet_capture.core import Propagator


class CodexPropagator(Propagator):
    name = "codex"
    order = 40
    optional = True
    source = Path("native/home/files/.codex/config.toml")
    target = Path(".codex/config.toml")

    def propagate(
        self, source_path: Path, target_path: Path, output_path: Path
    ) -> None:
        output_path.write_text(target_path.read_text())


PROPAGATOR = CodexPropagator()
