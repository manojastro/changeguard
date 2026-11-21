"""In-memory assessment store (demo/CI scope; swap for DB in prod)."""

from __future__ import annotations

from .models import AssessmentRecord

_STORE: dict[str, AssessmentRecord] = {}


def save(rec: AssessmentRecord) -> None:
    _STORE[rec.id] = rec


def get(rid: str) -> AssessmentRecord | None:
    return _STORE.get(rid)


def all_records() -> list[AssessmentRecord]:
    return list(_STORE.values())


def clear() -> None:
    _STORE.clear()
