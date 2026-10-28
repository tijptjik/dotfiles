"""Preserve ZapZap's live settings, including its recent download history."""

from __future__ import annotations

import json
import socket
from pathlib import Path

from fleet_capture.core import Propagator, UpdateError


class ZapZapPropagator(Propagator):
    name = "zapzap"
    order = 50
    optional = True
    source = Path("native/home/data/zapzap.json")
    target = Path(".config/ZapZap/ZapZap.conf")

    def propagate(
        self, source_path: Path, target_path: Path, output_path: Path
    ) -> None:
        # Preserve Qt's serialized values without parsing or rewriting the INI.
        data = json.loads(source_path.read_text())
        configs = data.get("zapzapConfigs")
        if not isinstance(configs, dict) or not all(
            isinstance(host, str) and isinstance(value, str)
            for host, value in configs.items()
        ):
            raise UpdateError("zapzapConfigs must map hostnames to configuration text")
        configs[socket.gethostname().split(".")[0]] = target_path.read_text()
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


PROPAGATOR = ZapZapPropagator()
