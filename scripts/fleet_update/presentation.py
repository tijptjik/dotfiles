"""Summarize hook status rows while retaining full output in per-run logs."""
import re
import os
from pathlib import Path
from dataclasses import dataclass

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ROW = re.compile(r"^([A-Z]+)\s+(✓|!|✗|X|-|\.\.\.)\s+(.*)$")
UNCHANGED = re.compile(r"(?:^|;\s*)no (?:changes|updates)$", re.IGNORECASE)


def timing_report(path, *, stream=None):
    """Optionally collect private timings without adding a terminal row."""
    export = os.environ.get("TJIKUP_TIMING_EXPORT")
    if export:
        try:
            content = Path(path).read_bytes()
            with os.fdopen(os.open(export, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
                output.write(content)
        except OSError:
            # Optional timing collection must not obscure the workflow result.
            pass


@dataclass
class Outcome:
    verb: str = "DONE"
    icon: str = "✓"
    note: str = ""
    warnings: tuple = ()


def summary(output):
    """Use emitted results, never the action the manifest hoped to perform."""
    rows = []
    warnings = []
    failed = False
    for line in ANSI.sub("", output).replace("\r", "\n").splitlines():
        match = ROW.match(line.strip())
        if match:
            verb, icon, content = match.groups()
            if icon == "...":
                continue
            if icon in {"!", "✗", "X"} or verb in {"WARN", "FAILED", "ERROR"}:
                warnings.append(line.strip())
                failed = failed or icon in {"✗", "X"} or verb in {"FAILED", "ERROR"}
                continue
            fields = re.split(r"\s{2,}", content, maxsplit=1)
            note = fields[1].strip() if len(fields) == 2 else ""
            if icon == "✓" and UNCHANGED.search(note):
                verb = "SKIP"
            rows.append((verb, icon, note))
        elif re.search(r"\b(warning|error|failed)\b", line, re.IGNORECASE):
            warnings.append(line.strip())
    # A later skipped substep must not hide an earlier mutation. Conversely,
    # a check and a set of skips do not establish that anything was updated.
    changed = [row for row in rows if row[0] not in {"SKIP", "CHECK", "DONE", "COMPLETE"}]
    selected = changed or [row for row in rows if row[0] == "CHECK"] or rows
    verbs = list(dict.fromkeys(row[0] for row in selected))
    verb = verbs[0] if len(verbs) == 1 else "APPLY" if changed else "DONE"
    notes = list(dict.fromkeys(row[2] for row in selected if row[2]))
    icon = "-" if selected and all(row[1] == "-" for row in selected) else "✓"
    if warnings:
        verb, icon = ("FAILED", "✗") if failed else ("WARN", "!")
    return Outcome(verb, icon, "; ".join(notes), tuple(warnings))
