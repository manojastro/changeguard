"""MCP tool stubs (P3 pattern). Reads are open; writes need approval."""

from __future__ import annotations

from .config import settings
from .history import load_history
from .models import HistoricalChange

_NOTES: dict[str, list[str]] = {}


def get_change(change_id: str) -> HistoricalChange | None:
    for h in load_history(settings.data_path):
        if h.id == change_id:
            return h
    return None


def list_change_collisions(change_id: str, window_hours: float = 2.0) -> list[str]:
    hist = load_history(settings.data_path)
    target = next((h for h in hist if h.id == change_id), None)
    if target is None:
        return []
    out = []
    for h in hist:
        if h.id == change_id:
            continue
        lhs = h.scheduled_at.replace(tzinfo=None)
        rhs = target.scheduled_at.replace(tzinfo=None)
        if abs((lhs - rhs).total_seconds()) <= window_hours * 3600:
            out.append(h.id)
    return out


def add_change_note(change_id: str, note: str, approved: bool = False) -> str:
    """Write path: approval-gated. Raises PermissionError without approval."""
    if not approved:
        raise PermissionError("add_change_note requires explicit CAB approval (approved=True)")
    _NOTES.setdefault(change_id, []).append(note)
    return f"note recorded on {change_id}"


def get_notes(change_id: str) -> list[str]:
    return list(_NOTES.get(change_id, []))
