"""Load generated history / hand changes (JSONL of HistoricalChange)."""

from __future__ import annotations

import json
from pathlib import Path

from .models import HistoricalChange


def load_history(path: str | Path) -> list[HistoricalChange]:
    items: list[HistoricalChange] = []
    p = Path(path)
    if not p.exists():
        return []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(HistoricalChange.model_validate(json.loads(line)))
    return sorted(items, key=lambda c: c.scheduled_at)
