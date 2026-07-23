"""Propagate scalar changes in Zed's JSONC settings."""

from __future__ import annotations

import json
from pathlib import Path

from tjikup.core import (
    TEMPLATE_ACTION,
    JsonSpanParser,
    Propagator,
    UpdateError,
    get_path,
    inside_range,
    load_jsonc,
    strip_jsonc_comments,
    template_control_ranges,
)


def update_template(source_path: Path, target_path: Path, output_path: Path) -> None:
    source = source_path.read_text()
    target = load_jsonc(target_path)
    masked = strip_jsonc_comments(source)
    masked_chars = list(masked)
    for match in TEMPLATE_ACTION.finditer(source):
        for index in range(match.start(), match.end()):
            if masked_chars[index] != "\n":
                masked_chars[index] = " "
    masked = "".join(masked_chars)

    parser = JsonSpanParser(masked)
    parser.parse()
    protected = template_control_ranges(source)
    replacements: list[tuple[int, int, str]] = []
    structural_paths: list[tuple[object, ...]] = []

    for path, spans in parser.spans.items():
        if not path or inside_range(*spans[-1], protected):
            continue
        try:
            target_value = get_path(target, path)
        except (KeyError, IndexError, TypeError):
            structural_paths.append(path)
            continue
        start, end = spans[-1]
        original_value = source[start:end]
        if "{{" in original_value or isinstance(target_value, (dict, list)):
            continue
        try:
            current_value = json.loads(masked[start:end])
        except json.JSONDecodeError:
            continue
        if current_value != target_value:
            replacements.append((start, end, json.dumps(target_value, ensure_ascii=False)))

    if structural_paths:
        paths = ", ".join(".".join(map(str, path)) for path in structural_paths[:5])
        raise UpdateError(f"Zed has structural changes that need a manual template merge: {paths}")

    updated = source
    for start, end, replacement in sorted(replacements, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    output_path.write_text(updated)


class ZedPropagator(Propagator):
    name = "zed"
    order = 10
    source = Path("home/dot_config/zed/private_settings.json.tmpl")
    target = Path(".config/zed/settings.json")

    def propagate(self, source_path: Path, target_path: Path, output_path: Path) -> None:
        update_template(source_path, target_path, output_path)


PROPAGATOR = ZedPropagator()
