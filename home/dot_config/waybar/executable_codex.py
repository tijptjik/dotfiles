#!/usr/bin/env python

import json
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = Path.home() / ".codex-lb" / "store.db"
# Codex now exposes the desired weekly stats through the primary window.
WEEKLY_WINDOW = "primary"
SUMMARY_LABEL = "󰃭"
TJK_WEIGHT = 20
TOOLTIP_HEADERS = {
    "percent": "1w%",
    "time": "1w↻",
}
QUERY = """
WITH latest_usage AS (
  SELECT
    a.id AS account_id,
    COALESCE(NULLIF(a.alias, ''), a.email) AS label,
    100.0 - uh.used_percent AS remaining_percent,
    uh.reset_at,
    ROW_NUMBER() OVER (
      PARTITION BY a.id
      ORDER BY uh.recorded_at DESC, uh.id DESC
    ) AS rn
  FROM accounts a
  JOIN usage_history uh ON uh.account_id = a.id
  WHERE a.status = 'active' AND uh.window = ?
)
SELECT
  account_id,
  label,
  remaining_percent,
  reset_at
FROM latest_usage
WHERE rn = 1
ORDER BY label;
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
        return connection.execute(QUERY, (WEEKLY_WINDOW,)).fetchall()
    finally:
        connection.close()


def build_payload(rows: list[sqlite3.Row]) -> dict[str, str]:
    accounts: dict[str, dict[str, object]] = {}
    for row in rows:
        accounts[row["label"]] = {
            "weekly": row["remaining_percent"],
            "weekly_reset_at": row["reset_at"],
        }

    weighted_values = [
        (account["weekly"], TJK_WEIGHT if label.casefold() == "tjk" else 1)
        for label, account in accounts.items()
        if account["weekly"] is not None
    ]
    total_weight = sum(weight for _, weight in weighted_values)
    weekly_average = (
        sum(value * weight for value, weight in weighted_values) / total_weight
        if total_weight
        else None
    )

    text = f"{SUMMARY_LABEL} {format_percent(weekly_average)}"

    now = int(time.time())
    label_width = max((len(label) for label in accounts), default=5)
    header = "  ".join(
        [
            "acct".ljust(label_width),
            TOOLTIP_HEADERS["percent"].rjust(4),
            TOOLTIP_HEADERS["time"].rjust(4),
        ]
    )
    lines = [header]

    for label, values in sorted(accounts.items()):
        lines.append(
            "  ".join(
                [
                    label.ljust(label_width),
                    format_percent(values["weekly"], 1).rjust(5),
                    format_time_until_reset(values["weekly_reset_at"], now).rjust(5),
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
            "text": "󰃭 -",
            "tooltip": f"Missing database: {DB_PATH}",
            "alt": "codex-missing",
            "class": "custom-codex",
        }
    else:
        try:
            payload = build_payload(load_rows())
        except Exception as error:
            payload = {
                "text": "󰃭 -",
                "tooltip": f"Codex usage error: {error}",
                "alt": "codex-error",
                "class": "custom-codex",
            }

    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
