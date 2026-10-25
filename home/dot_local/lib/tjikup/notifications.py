"""Best-effort local desktop completion reports; never affect the update result."""

from html import escape
import os
from pathlib import Path
import shutil
import subprocess


def completion_message(report_file, result, seconds, *, dry_run=False, interrupted=False):
    records = []
    unavailable = False
    try:
        if report_file is not None:
            for line in report_file.read_text().splitlines():
                fields = tuple(line.split("\t", 3))
                if len(fields) == 4 and fields not in records:
                    records.append(fields)
        else:
            unavailable = True
    except (OSError, UnicodeError):
        unavailable = True
    issues = [row for row in records if row[1] in {"!", "✗", "X"}]
    failed = result != 0 or any(row[1] in {"✗", "X"} for row in issues)
    if interrupted:
        state = "interrupted"
    elif failed:
        state = "failed"
    elif issues or unavailable:
        state = "needs attention"
    else:
        state = "complete"
    title = f"Tjikup{' preview' if dry_run else ''} {state}"
    minutes, seconds = divmod(max(0, int(seconds)), 60)
    duration = f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"
    completed = len({(row[0], row[2]) for row in records if row[1] == "✓"})
    body = [f"{duration} · Stages completed: {completed} · Issues: {len(issues)}"]
    if dry_run:
        body.append("Preview only; no changes applied.")
    if unavailable:
        body.append("Stage report unavailable; check the terminal.")
    # Do not copy command output or exception details into desktop history.
    for stage, icon, subject, _ in issues[:3]:
        body.append(f"{icon} {stage}: {' '.join(subject.split())[:100]}")
    if len(issues) > 3:
        body.append(f"… and {len(issues) - 3} more")
    if failed or issues:
        body.append("See terminal output for details.")
    return title, escape("\n".join(body)), "critical" if failed else "normal"


def notify_completion(report_file, result, seconds, *, dry_run=False, interrupted=False):
    if os.environ.get("TJIKUP_NOTIFY") == "0" or os.environ.get("SSH_CONNECTION"):
        return
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        return
    sender = shutil.which("notify-send")
    if sender is None:
        return
    try:
        title, body, urgency = completion_message(
            report_file, result, seconds, dry_run=dry_run, interrupted=interrupted,
        )
        icon = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "icons/tjikup.png"
        subprocess.run(
            [sender, "--app-name=Tjikup", f"--icon={icon}", f"--urgency={urgency}",
             "--expire-time=10000", title, body],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
