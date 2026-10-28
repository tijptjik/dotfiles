"""Summarize hook status rows while retaining full output in per-run logs."""
import re
import os
from pathlib import Path
import socket
import sys
from dataclasses import dataclass
from urllib.parse import urlsplit

from tjikup import runtime

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ROW = re.compile(r"^([A-Z]+)\s+(✓|!|✗|X|-|\.\.\.)\s+(.*)$")
UNCHANGED = re.compile(r"(?:^|;\s*)no (?:changes|updates)$", re.IGNORECASE)


def timing_report(path, *, stream=None):
    """Link the private report compactly; retain full paths in ordinary logs."""
    stream = sys.stdout if stream is None else stream
    path = Path(path).absolute()
    # Remote shortcuts collect this private copy after SSH exits, then emit a
    # local file link. Neither xdg-open nor Kitty can recover an expired SSH
    # connection from a remote file:// hostname alone.
    export = os.environ.get("TJIKUP_TIMING_EXPORT")
    if export:
        try:
            content = path.read_bytes()
            with os.fdopen(os.open(export, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
                output.write(content)
            return
        except OSError as error:
            print(f"Could not collect task timings: {error}", file=stream, flush=True)
    interactive = stream.isatty() or os.environ.get("TJIKUP_PROGRESS") == "1"
    if not interactive or os.environ.get("TERM") == "dumb":
        print(f"Task timings: {path}", file=stream, flush=True)
        return

    title = "Task timings"
    note = path.parent.name if runtime.terminal_columns() >= 40 else None
    row = runtime.format_status("REPORT", "↗", title, note)
    url = path.as_uri()
    if os.environ.get("SSH_CONNECTION"):
        # Direct interactive SSH sessions still need the originating hostname.
        url = urlsplit(url)._replace(netloc=socket.gethostname()).geturl()
    label = f"\033[36m{title}\033[0m" if runtime.use_color() else title
    link = f"\033]8;;{url}\033\\{label}\033]8;;\033\\"
    print(row.replace(title, link, 1), file=stream, flush=True)


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
