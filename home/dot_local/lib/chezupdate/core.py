"""Shared primitives for chezupdate propagators."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable


TEMPLATE_ACTION = re.compile(r"{{.*?}}", re.DOTALL)


class UpdateError(RuntimeError):
    pass


class Propagator(ABC):
    """One live configuration file and its chezmoi source template."""

    name: str
    source: Path
    target: Path

    @abstractmethod
    def propagate(self, source_path: Path, target_path: Path, output_path: Path) -> None:
        """Write an updated template to output_path."""


def load_jsonc(path: Path) -> Any:
    return json.loads(strip_jsonc_comments(path.read_text()))


def strip_jsonc_comments(text: str) -> str:
    """Remove JSONC comments without changing strings or line positions."""
    chars = list(text)
    in_string = False
    escaped = False
    index = 0
    while index < len(chars):
        char = chars[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == "/" and index + 1 < len(chars) and chars[index + 1] == "/":
            chars[index] = chars[index + 1] = " "
            index += 2
            while index < len(chars) and chars[index] != "\n":
                chars[index] = " "
                index += 1
            continue
        if char == "/" and index + 1 < len(chars) and chars[index + 1] == "*":
            chars[index] = chars[index + 1] = " "
            index += 2
            while index + 1 < len(chars) and not (chars[index] == "*" and chars[index + 1] == "/"):
                if chars[index] != "\n":
                    chars[index] = " "
                index += 1
            if index + 1 < len(chars):
                chars[index] = chars[index + 1] = " "
                index += 2
            continue
        index += 1
    return "".join(chars)


class JsonSpanParser:
    """Small JSONC parser that records source spans for each JSON path."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.index = 0
        self.spans: dict[tuple[Any, ...], list[tuple[int, int]]] = {}

    def parse(self) -> None:
        self.skip_space()
        self.parse_value(())
        self.skip_space()
        if self.index != len(self.text):
            raise UpdateError(f"could not parse template JSON near offset {self.index}")

    def skip_space(self) -> None:
        while self.index < len(self.text) and self.text[self.index].isspace():
            self.index += 1

    def parse_value(self, path: tuple[Any, ...]) -> None:
        self.skip_space()
        start = self.index
        if self.index >= len(self.text):
            raise UpdateError("unexpected end of template JSON")
        char = self.text[self.index]
        if char == "{":
            self.parse_object(path)
        elif char == "[":
            self.parse_array(path)
        elif char == '"':
            self.parse_string()
        else:
            while self.index < len(self.text) and self.text[self.index] not in ",]}" and not self.text[self.index].isspace():
                self.index += 1
        self.spans.setdefault(path, []).append((start, self.index))

    def parse_string(self) -> None:
        self.index += 1
        escaped = False
        while self.index < len(self.text):
            char = self.text[self.index]
            self.index += 1
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                return
        raise UpdateError("unterminated JSON string in template")

    def parse_object(self, path: tuple[Any, ...]) -> None:
        self.index += 1
        self.skip_space()
        if self.index < len(self.text) and self.text[self.index] == "}":
            self.index += 1
            return
        while True:
            self.skip_space()
            key_start = self.index
            self.parse_string()
            key = json.loads(self.text[key_start : self.index])
            self.skip_space()
            if self.index >= len(self.text) or self.text[self.index] != ":":
                raise UpdateError(f"expected ':' near offset {self.index}")
            self.index += 1
            self.parse_value((*path, key))
            self.skip_space()
            if self.index < len(self.text) and self.text[self.index] == "}":
                self.index += 1
                return
            if self.index >= len(self.text) or self.text[self.index] != ",":
                raise UpdateError(f"expected ',' or '}}' near offset {self.index}")
            self.index += 1

    def parse_array(self, path: tuple[Any, ...]) -> None:
        self.index += 1
        self.skip_space()
        item = 0
        if self.index < len(self.text) and self.text[self.index] == "]":
            self.index += 1
            return
        while True:
            self.parse_value((*path, item))
            item += 1
            self.skip_space()
            if self.index < len(self.text) and self.text[self.index] == "]":
                self.index += 1
                return
            if self.index >= len(self.text) or self.text[self.index] != ",":
                raise UpdateError(f"expected ',' or ']' near offset {self.index}")
            self.index += 1


def template_control_ranges(source: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    stack: list[int] = []
    for match in TEMPLATE_ACTION.finditer(source):
        body = match.group(0)[2:-2].strip(" -\t\r\n")
        if re.match(r"(?:if|with|range)\b", body):
            stack.append(match.start())
        elif re.match(r"end\b", body) and stack:
            ranges.append((stack.pop(), match.end()))
    return ranges


def inside_range(start: int, end: int, ranges: Iterable[tuple[int, int]]) -> bool:
    return any(range_start <= start and end <= range_end for range_start, range_end in ranges)


def get_path(value: Any, path: tuple[Any, ...]) -> Any:
    for key in path:
        value = value[key]
    return value
