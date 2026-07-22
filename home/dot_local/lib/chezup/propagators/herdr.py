"""Propagate Herdr's persisted session state."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from chezup.core import TEMPLATE_ACTION, Propagator, UpdateError, load_jsonc


HOME_ACTION = re.compile(r"{{\s*\.chezmoi\.homeDir\s*}}")


def preserve_template_strings(value: Any, source_value: Any, home_dir: str, expression: str) -> Any:
    if isinstance(value, dict):
        source_dict = source_value if isinstance(source_value, dict) else {}
        return {
            key: preserve_template_strings(item, source_dict.get(key), home_dir, expression)
            for key, item in value.items()
        }
    if isinstance(value, list):
        source_list = source_value if isinstance(source_value, list) else []
        return [
            preserve_template_strings(item, source_list[index] if index < len(source_list) else None, home_dir, expression)
            for index, item in enumerate(value)
        ]
    if isinstance(source_value, str) and "{{" in source_value:
        if HOME_ACTION.search(source_value) and isinstance(value, str) and (
            value == home_dir or value.startswith(home_dir + os.sep)
        ):
            return expression + value[len(home_dir) :]
        return source_value
    if isinstance(value, str) and (value == home_dir or value.startswith(home_dir + os.sep)):
        return expression + value[len(home_dir) :]
    return value


class HerdrPropagator(Propagator):
    name = "herdr"
    order = 20
    source = Path("home/dot_config/herdr/session.json.tmpl")
    target = Path(".config/herdr/session.json")

    def propagate(self, source_path: Path, target_path: Path, output_path: Path) -> None:
        source_text = source_path.read_text()
        source = json.loads(source_text)
        target = load_jsonc(target_path)

        actions = [action.group(0) for action in TEMPLATE_ACTION.finditer(source_text)]
        control_actions = [action for action in actions if re.search(r"\b(if|else|end|range|with)\b", action)]
        if control_actions:
            raise UpdateError(f"unsupported control template action in {source_path}")

        home_action = next(iter(HOME_ACTION.finditer(source_text)), None)
        expression = home_action.group(0) if home_action else "{{ .chezmoi.homeDir }}"
        updated = preserve_template_strings(target, source, str(Path.home()), expression)
        output_path.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n")


PROPAGATOR = HerdrPropagator()
