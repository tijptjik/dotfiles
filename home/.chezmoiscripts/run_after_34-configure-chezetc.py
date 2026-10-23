#!/usr/bin/env python3
"""Keep tjikup's output and reporting environment across chezetc's sudo."""

from pathlib import Path
import re


TJIKUP_ENV = (
    "TJIKUP_COLOR",
    "TJIKUP_NO_SPIN",
    "TJIKUP_REPORT_FILE",
    "TJIKUP_SKIP_PREFLIGHT",
    "TJIKUP_COLUMNS",
)


def configure_chezetc(wrapper: Path) -> None:
    if not wrapper.is_file():
        return

    source = wrapper.read_text()
    # Extend only the upstream wrapper's explicit allowlist. Do not preserve
    # the whole environment or replace any other local wrapper customizations.
    pattern = r"(?m)^sudo --preserve-env=([A-Za-z0-9_,]+)(?= --)"
    matches = list(re.finditer(pattern, source))
    if len(matches) != 1:
        raise RuntimeError(f"unrecognized sudo environment allowlist in {wrapper}")
    match = matches[0]
    names = match.group(1).split(",")
    names.extend(name for name in TJIKUP_ENV if name not in names)
    updated = source[:match.start(1)] + ",".join(names) + source[match.end(1):]
    if updated != source:
        wrapper.write_text(updated)


if __name__ == "__main__":
    configure_chezetc(Path.home() / ".tools/chezetc/chezetc")
