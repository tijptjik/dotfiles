"""Propagate Solaar's device configuration into the chezmoi source tree."""

from __future__ import annotations

from pathlib import Path

from chezup.core import Propagator


class SolaarPropagator(Propagator):
    name = "solaar"
    order = 30
    source = Path("home/dot_config/solaar/config.yaml")
    target = Path(".config/solaar/config.yaml")

    def propagate(self, source_path: Path, target_path: Path, output_path: Path) -> None:
        output_path.write_text(target_path.read_text())


PROPAGATOR = SolaarPropagator()
