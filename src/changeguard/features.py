"""Deterministic risk features (all code, no LLM)."""

from __future__ import annotations

from datetime import datetime

from .cmdb import blast_radius, criticality
from .models import BAD_OUTCOMES, ChangeRequest, HistoricalChange, RiskFeatures
from .retrieval import retrieve_similar

FREEZE_WINDOWS: list[tuple[datetime, datetime]] = [
    (datetime(2024, 12, 20), datetime(2025, 1, 5)),
]

OFF_HOURS = set(range(0, 7)) | {22, 23}


def in_freeze(when: datetime) -> bool:
    naive = when.replace(tzinfo=None)
    return any(start <= naive <= end for start, end in FREEZE_WINDOWS)


def window_risk(when: datetime) -> float:
    """0.0 business hours, 0.6 weekend, 0.8 off-hours, 1.0 both."""
    risk = 0.0
    if when.weekday() >= 5:
        risk = max(risk, 0.6)
    if when.hour in OFF_HOURS:
        risk = max(risk, 0.8)
    if when.weekday() >= 5 and when.hour in OFF_HOURS:
        risk = 1.0
    return risk


def collision_count(cr: ChangeRequest, history: list[HistoricalChange]) -> int:
    """Other changes within +/-2h of the CR's schedule."""
    n = 0
    for h in history:
        if h.id == cr.id:
            continue
        lhs = h.scheduled_at.replace(tzinfo=None)
        rhs = cr.scheduled_at.replace(tzinfo=None)
        if abs((lhs - rhs).total_seconds()) <= 2 * 3600:
            n += 1
    return n


def past_failure_rate(cr: ChangeRequest, history: list[HistoricalChange], top_k: int = 5) -> float:
    sims = retrieve_similar(cr, history, top_k=top_k)
    if not sims:
        return 0.0
    bad = sum(1 for h, _ in sims if h.outcome in BAD_OUTCOMES)
    return bad / len(sims)


def requester_fail_rate(cr: ChangeRequest, history: list[HistoricalChange]) -> float:
    mine = [h for h in history if h.requester == cr.requester and h.id != cr.id]
    if not mine:
        return 0.0
    bad = sum(1 for h in mine if h.outcome in BAD_OUTCOMES)
    return bad / len(mine)


def build_features(cr: ChangeRequest, history: list[HistoricalChange]) -> RiskFeatures:
    try:
        scope = blast_radius(cr.ci)
        crit = criticality(cr.ci)
    except KeyError:
        scope = [cr.ci]
        crit = 10.0  # unknown CI -> assume worst (fail-closed, see F1)
    return RiskFeatures(
        blast_radius_size=len(scope),
        ci_criticality=crit,
        collision_count=collision_count(cr, history),
        freeze_window=in_freeze(cr.scheduled_at),
        rollback_present=cr.rollback_plan_present,
        rollback_tested=cr.rollback_plan_tested,
        past_failure_rate=past_failure_rate(cr, history),
        window_risk=window_risk(cr.scheduled_at),
        requester_fail_rate=requester_fail_rate(cr, history),
        test_evidence=cr.test_evidence,
    )
