"""Summarize hook status rows while retaining full output in per-run logs."""
import re

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ROW = re.compile(r"^([A-Z]+)\s+(✓|!|✗|X|-|\.\.\.)\s+(.*)$")


def summary(output):
    note = ""
    warnings = []
    for line in ANSI.sub("", output).replace("\r", "\n").splitlines():
        match = ROW.match(line.strip())
        if match:
            verb, icon, content = match.groups()
            if icon == "...":
                continue
            if icon in {"!", "✗", "X"} or verb in {"WARN", "FAILED", "ERROR"}:
                warnings.append(line.strip())
            fields = re.split(r"\s{2,}", content, maxsplit=1)
            if len(fields) == 2:
                note = fields[1]
        elif re.search(r"\b(warning|error|failed)\b", line, re.IGNORECASE):
            warnings.append(line.strip())
    return note, warnings
