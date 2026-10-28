"""Propagate Solaar's device configuration into the native source tree."""

from __future__ import annotations

from pathlib import Path

from fleet_capture.core import Propagator


class SolaarPropagator(Propagator):
    name = "solaar"
    order = 30
    optional = True
    source = Path("native/home/files/.config/solaar/config.yaml")
    target = Path(".config/solaar/config.yaml")

    def propagate(
        self, source_path: Path, target_path: Path, output_path: Path
    ) -> None:
        output_path.write_text(target_path.read_text())


PROPAGATOR = SolaarPropagator()
