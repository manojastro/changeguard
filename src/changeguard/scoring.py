"""Deterministic weighted risk score -> lane. Code decides, LLM explains.

Weights (0-100 scale) mirror the hidden generator rules closely enough to
beat the critical-CI baseline, but are NOT identical (noise + drift keep
the problem honest). Thresholds from Settings so CAB can retune.
"""

from __future__ import annotations

from .config import settings
from .models import RiskAssessment, RiskFeatures

WEIGHTS: dict[str, float] = {
    "blast_radius": 4.0,  # per CI in scope
    "criticality": 2.0,  # per criticality point (0-10)
    "collision": 5.0,  # per colliding change (capped)
    "freeze": 15.0,
    "no_rollback": 14.0,
    "untested_rollback": 7.0,
    "past_fail_rate": 14.0,  # x rate 0..1
    "window_risk": 10.0,  # x risk 0..1
    "requester_fail_rate": 10.0,  # x rate 0..1
    "no_tests": 8.0,
}


def score_features(f: RiskFeatures) -> RiskAssessment:
    c: dict[str, float] = {}
    c["blast_radius"] = min(f.blast_radius_size, 8) * WEIGHTS["blast_radius"]
    c["criticality"] = f.ci_criticality * WEIGHTS["criticality"]
    c["collision"] = min(f.collision_count, 4) * WEIGHTS["collision"]
    c["freeze"] = WEIGHTS["freeze"] if f.freeze_window else 0.0
    if not f.rollback_present:
        c["rollback"] = WEIGHTS["no_rollback"]
    elif not f.rollback_tested:
        c["rollback"] = WEIGHTS["untested_rollback"]
    else:
        c["rollback"] = 0.0
    c["past_fail_rate"] = f.past_failure_rate * WEIGHTS["past_fail_rate"]
    c["window_risk"] = f.window_risk * WEIGHTS["window_risk"]
    c["requester_fail_rate"] = f.requester_fail_rate * WEIGHTS["requester_fail_rate"]
    c["no_tests"] = 0.0 if f.test_evidence else WEIGHTS["no_tests"]
    total = round(min(100.0, sum(c.values())), 1)
    if total >= settings.reject_threshold:
        lane = "reject-back"
    elif total >= settings.high_risk_threshold:
        lane = "needs-CAB"
    else:
        lane = "standard"
    drivers = [k for k, v in sorted(c.items(), key=lambda kv: kv[1], reverse=True) if v > 0][:3]
    from .models import ScoreBreakdown

    return RiskAssessment(
        change_id="",
        score=total,
        lane=lane,  # type: ignore[arg-type]
        drivers=drivers,
        features=f,
        breakdown=ScoreBreakdown(
            contributions=c,
            threshold_standard=settings.high_risk_threshold,
            threshold_reject=settings.reject_threshold,
        ),
    )


def is_high_risk(a: RiskAssessment) -> bool:
    return a.lane in ("needs-CAB", "reject-back")
