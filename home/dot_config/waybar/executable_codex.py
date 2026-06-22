#!/usr/bin/env python

import json
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = Path.home() / ".codex-lb" / "store.db"
WINDOWS = ("primary", "secondary")
SUMMARY_LABELS = {
    "primary": "󱑂",
    "secondary": "󰃭",
}
TOOLTIP_HEADERS = {
    "primary_percent": "5h%",
    "primary_time": "5h↻",
    "secondary_percent": "1w%",
    "secondary_time": "1w↻",
}
QUERY = """
WITH latest_usage AS (
  SELECT
    a.id AS account_id,
    COALESCE(NULLIF(a.alias, ''), a.email) AS label,
    COALESCE(uh.window, 'primary') AS window_name,
    100.0 - uh.used_percent AS remaining_percent,
    uh.reset_at,
    ROW_NUMBER() OVER (
      PARTITION BY a.id, COALESCE(uh.window, 'primary')
      ORDER BY uh.recorded_at DESC, uh.id DESC
    ) AS rn
  FROM accounts a
  JOIN usage_history uh ON uh.account_id = a.id
  WHERE a.status = 'active'
)
SELECT
  account_id,
  label,
  window_name,
  remaining_percent,
  reset_at
FROM latest_usage
WHERE rn = 1
ORDER BY label, window_name;
"""


def format_percent(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "-"
    if digits == 0:
        return f"{round(value):.0f}%"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".") + "%"


def format_time_until_reset(reset_at: int | None, now: int) -> str:
    if reset_at is None:
        return "-"

    seconds = max(0, int(reset_at) - now)
    minutes, _ = divmod(seconds, 60)
    days, minutes = divmod(minutes, 60 * 24)
    hours, minutes = divmod(minutes, 60)

    if days > 0:
        return f"{days}d{hours}h"
    if hours > 0:
        return f"{hours}h{minutes}m"
    return f"{minutes}m"


def load_rows() -> list[sqlite3.Row]:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(QUERY).fetchall()
    finally:
        connection.close()


def build_payload(rows: list[sqlite3.Row]) -> dict[str, str]:
    accounts: dict[str, dict[str, object]] = {}
    for row in rows:
        entry = accounts.setdefault(
            row["label"],
            {
                "primary": None,
                "secondary": None,
                "primary_reset_at": None,
                "secondary_reset_at": None,
            },
        )
        entry[row["window_name"]] = row["remaining_percent"]
        entry[f"{row['window_name']}_reset_at"] = row["reset_at"]

    averages = {}
    for window_name in WINDOWS:
        values = [
            account[window_name]
            for account in accounts.values()
            if account[window_name] is not None
        ]
        averages[window_name] = sum(values) / len(values) if values else None

    text = " ".join(
        f"{SUMMARY_LABELS[window_name]} {format_percent(averages[window_name])}"
        for window_name in WINDOWS
    )

    now = int(time.time())
    label_width = max((len(label) for label in accounts), default=5)
    header = "  ".join(
        [
            "acct".ljust(label_width),
            TOOLTIP_HEADERS["primary_percent"].rjust(4),
            TOOLTIP_HEADERS["primary_time"].rjust(4),
            TOOLTIP_HEADERS["secondary_percent"].rjust(5),
            TOOLTIP_HEADERS["secondary_time"].rjust(4),
        ]
    )
    lines = [header]

    for label, values in sorted(accounts.items()):
        lines.append(
            "  ".join(
                [
                    label.ljust(label_width),
                    format_percent(values["primary"], 1).rjust(5),
                    format_time_until_reset(values["primary_reset_at"], now).rjust(5),
                    format_percent(values["secondary"], 1).rjust(5),
                    format_time_until_reset(values["secondary_reset_at"], now).rjust(4),
                ]
            )
        )

    return {
        "text": text,
        "tooltip": "\n".join(lines) if len(lines) > 1 else "No active Codex accounts",
        "alt": "codex",
        "class": "custom-codex",
    }


def main() -> None:
    if not DB_PATH.exists():
        payload = {
            "text": "󱑂 - 󰃭 -",
            "tooltip": f"Missing database: {DB_PATH}",
            "alt": "codex-missing",
            "class": "custom-codex",
        }
    else:
        try:
            payload = build_payload(load_rows())
        except Exception as error:
            payload = {
                "text": "󱑂 - 󰃭 -",
                "tooltip": f"Codex usage error: {error}",
                "alt": "codex-error",
                "class": "custom-codex",
            }

    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
