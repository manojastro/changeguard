"""Shared fixtures: tiny synthetic history (no data files needed)."""

from __future__ import annotations

import pytest

from changeguard.models import ChangeRequest, HistoricalChange


def cr(**kw) -> ChangeRequest:
    base = dict(id="CR-T1", title="Index rebuild on orders-db", description="Rebuild index on orders table",
                ci="orders-db", change_type="normal", scheduled_at="2025-03-14T22:30:00",
                requester="rel-eng-01", rollback_plan_present=True, rollback_plan_tested=True,
                test_evidence=True)
    base.update(kw)
    return ChangeRequest.model_validate(base)


def hcr(i: int, **kw) -> HistoricalChange:
    base = dict(id=f"CH-{i:04d}", title=f"Change {i} on orders-db", description="Index rebuild orders table",
                ci="orders-db", change_type="normal", scheduled_at=f"2025-01-{i+1:02d}T10:00:00",
                requester="rel-eng-01", rollback_plan_present=True, rollback_plan_tested=True,
                test_evidence=True, outcome="success", blast_radius=5, linked_incidents=[])
    base.update(kw)
    return HistoricalChange.model_validate(base)


@pytest.fixture
def history() -> list[HistoricalChange]:
    return [
        hcr(1, outcome="success"),
        hcr(2, outcome="failed", rollback_plan_present=False, rollback_plan_tested=False),
        hcr(3, outcome="caused-incident", ci="payments-api", linked_incidents=["INC-1001"]),
        hcr(4, outcome="success", ci="cms-web", title="Copy update on cms-web"),
        hcr(5, outcome="rolled-back", rollback_plan_present=True, rollback_plan_tested=False),
    ]


@pytest.fixture
def change() -> ChangeRequest:
    return cr()
