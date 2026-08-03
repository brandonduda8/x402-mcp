"""Read/write agent-ops ledger jsonl files for mission-control dashboard."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger"


def read_ledger_rows(name: str, *, limit: int = 1000) -> list[dict]:
    """Parse spend.jsonl or revenue.jsonl; newest first, capped."""
    if name not in ("spend", "revenue"):
        raise ValueError("ledger name must be spend or revenue")

    path = LEDGER / f"{name}.jsonl"
    if not path.exists():
        return []

    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    rows.reverse()
    return rows[:limit]


def append_ledger_row(name: str, row: dict[str, Any]) -> None:
    """Append one spend/revenue event. Never raises into request path."""
    if name not in ("spend", "revenue"):
        return
    try:
        LEDGER.mkdir(parents=True, exist_ok=True)
        path = LEDGER / f"{name}.jsonl"
        payload = {"ts": datetime.now(UTC).isoformat(), **row}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass