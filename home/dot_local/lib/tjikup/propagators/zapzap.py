"""Preserve ZapZap's live settings, including its recent download history."""

from __future__ import annotations

from pathlib import Path

from tjikup.core import Propagator


class ZapZapPropagator(Propagator):
    name = "zapzap"
    order = 50
    optional = True
    source = Path("home/dot_config/ZapZap/ZapZap.conf")
    target = Path(".config/ZapZap/ZapZap.conf")

    def propagate(self, source_path: Path, target_path: Path, output_path: Path) -> None:
        # Preserve Qt's serialized values without parsing or rewriting the INI.
        output_path.write_text(target_path.read_text())


PROPAGATOR = ZapZapPropagator()
