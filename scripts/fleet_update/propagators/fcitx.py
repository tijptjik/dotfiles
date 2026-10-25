"""Preserve Fcitx's live group order and input-method selection."""

from pathlib import Path

from fleet_update.core import Propagator


class FcitxPropagator(Propagator):
    name = "fcitx"
    order = 35
    optional = True
    backup_live = True
    source = Path("home/dot_config/fcitx5/private_profile")
    target = Path(".config/fcitx5/profile")

    def propagate(
        self, source_path: Path, target_path: Path, output_path: Path
    ) -> None:
        # Group order and DefaultIM are live user preferences, not formatting.
        output_path.write_bytes(target_path.read_bytes())


PROPAGATOR = FcitxPropagator()
