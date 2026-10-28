"""Fleet-owned status rows use the same icon renderer as application tasks."""
import io
import re
import sys

from tjikup import runtime
from .icons import HookProgress
from .icon_catalog import SERVICE_ICONS
from .presentation import ANSI, ROW


def stage_label(verb, icon, subject, note=None):
    if runtime.ACTIVE_STAGE:
        sys.stdout.write("\r\033[2K")
    runtime.ACTIVE_STAGE = False
    HookProgress(live=False).finish(subject, subject, verb=verb, icon=icon, note=note or "")


def stage_result(verb, subject, note=None):
    stage_label(verb, "✓", subject, note)


def stage_unchanged(subject, note="no changes"):
    stage_label("SKIP", "✓", subject, note)


def stage_expected(subject, note):
    stage_unchanged(subject, note)


def stage_skip(subject, note=None):
    stage_label("SKIP", "-", subject, note)


def decorate_native_row(line):
    """Decorate before-apply hook rows without recording their events twice."""
    match = ROW.match(ANSI.sub("", line).strip())
    if not match:
        return line
    verb, icon, content = match.groups()
    if icon == "...":
        # Fish replaces this one-line pending row with the completed result.
        # Expanding it to two lines would break its carriage-return contract.
        return line
    fields = re.split(r"\s{2,}", content, maxsplit=1)
    label = fields[0]
    if label == "Bitwarden CLIs":
        label = "Bitwarden (CLIs)"
    elif label == "Assets (user fonts)":
        label = "Assets (font folder migration)"
    if label.partition(' (')[0] not in SERVICE_ICONS:
        return line
    output = io.StringIO()
    progress = HookProgress(stream=output, live=False)
    progress.finish(label, label, verb=verb, icon=icon,
                    note=fields[1] if len(fields) == 2 else "", record=False)
    clear = "\033[2K" if "\033[2K" in line else ""
    return clear + output.getvalue().rstrip("\n")
