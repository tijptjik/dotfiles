#!/usr/bin/env python

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".codex-lb" / "store.db"
WINDOW_LABELS = {
    "primary": "5h",
    "secondary": "1w",
}
SUMMARY_LABELS = {
    "primary": "5h",
    "secondary": "w",
}
QUERY = """
WITH latest_usage AS (
  SELECT
    a.id AS account_id,
    COALESCE(NULLIF(a.alias, ''), a.email) AS label,
    COALESCE(uh.window, 'primary') AS window_name,
    100.0 - uh.used_percent AS remaining_percent,
    ROW_NUMBER() OVER (
      PARTITION BY a.id, COALESCE(uh.window, 'primary')
      ORDER BY uh.recorded_at DESC, uh.id DESC
    ) AS rn
  FROM accounts a
  JOIN usage_history uh ON uh.account_id = a.id
  WHERE a.status = 'active'
),
latest_credits AS (
  SELECT
    a.id AS account_id,
    uh.credits_balance,
    uh.credits_has,
    uh.credits_unlimited,
    ROW_NUMBER() OVER (
      PARTITION BY a.id
      ORDER BY
        CASE
          WHEN uh.credits_balance IS NOT NULL
            OR uh.credits_has IS NOT NULL
            OR uh.credits_unlimited IS NOT NULL
          THEN 0
          ELSE 1
        END,
        uh.recorded_at DESC,
        uh.id DESC
    ) AS rn
  FROM accounts a
  JOIN usage_history uh ON uh.account_id = a.id
  WHERE a.status = 'active'
)
SELECT
  lu.account_id,
  lu.label,
  lu.window_name,
  lu.remaining_percent,
  lc.credits_balance,
  lc.credits_has,
  lc.credits_unlimited
FROM latest_usage lu
LEFT JOIN latest_credits lc
  ON lc.account_id = lu.account_id AND lc.rn = 1
WHERE lu.rn = 1
ORDER BY lu.label, lu.window_name;
"""


def format_percent(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "-"
    if digits == 0:
        return f"{round(value):.0f}%"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".") + "%"


def format_credits(balance: float | None, has_credits: int | None, unlimited: int | None) -> str:
    if unlimited:
        return "inf"
    if balance is None:
        return "-" if not has_credits else "?"
    return f"{balance:.1f}".rstrip("0").rstrip(".")


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
                "credits_balance": row["credits_balance"],
                "credits_has": row["credits_has"],
                "credits_unlimited": row["credits_unlimited"],
            },
        )
        entry[row["window_name"]] = row["remaining_percent"]
        if entry["credits_balance"] is None and row["credits_balance"] is not None:
            entry["credits_balance"] = row["credits_balance"]
        if row["credits_has"] is not None:
            entry["credits_has"] = row["credits_has"]
        if row["credits_unlimited"] is not None:
            entry["credits_unlimited"] = row["credits_unlimited"]

    averages = {}
    for window_name in WINDOW_LABELS:
        values = [
            account[window_name]
            for account in accounts.values()
            if account[window_name] is not None
        ]
        averages[window_name] = sum(values) / len(values) if values else None

    text = " ".join(
        f"{SUMMARY_LABELS[window_name]}: {format_percent(averages[window_name])}"
        for window_name in ("primary", "secondary")
    )

    label_width = max((len(label) for label in accounts), default=5)
    header = f"{'acct'.ljust(label_width)}  {'5h':>5}  {'1w':>5}  {'cr':>6}"
    lines = [header]
    for label, values in sorted(accounts.items()):
        lines.append(
            "  ".join(
                [
                    label.ljust(label_width),
                    format_percent(values["primary"], 1).rjust(5),
                    format_percent(values["secondary"], 1).rjust(5),
                    format_credits(
                        values["credits_balance"],
                        values["credits_has"],
                        values["credits_unlimited"],
                    ).rjust(6),
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
            "text": "5h: - w: -",
            "tooltip": f"Missing database: {DB_PATH}",
            "alt": "codex-missing",
            "class": "custom-codex",
        }
    else:
        try:
            payload = build_payload(load_rows())
        except Exception as error:
            payload = {
                "text": "5h: - w: -",
                "tooltip": f"Codex usage error: {error}",
                "alt": "codex-error",
                "class": "custom-codex",
            }

    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
