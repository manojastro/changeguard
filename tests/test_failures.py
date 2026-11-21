"""5 failure demos as regression tests (see docs/failures.md).

F1 missing CMDB · F2 conflicting history · F3 risky-looking-but-safe ·
F4 invented reason caught by critic · F5 budget exhausted.
"""

from conftest import cr, hcr

from changeguard import gateway
from changeguard.critic import check_grounding
from changeguard.explain import build_evidence
from changeguard.features import build_features
from changeguard.models import Explanation, ExplanationClaim
from changeguard.scoring import score_features


def test_f1_missing_cmdb_fail_closed(history):
    f = build_features(cr(ci="ghost-ci-99"), history)
    assert f.ci_criticality == 10  # fail-closed, never fail-open
    assert score_features(f).lane in ("needs-CAB", "reject-back")


def test_f2_conflicting_history_still_scores():
    hist = [hcr(1, outcome="success"), hcr(2, outcome="caused-incident"),
            hcr(3, outcome="success"), hcr(4, outcome="rolled-back")]
    f = build_features(cr(), hist)
    assert f.past_failure_rate == 0.5
    assert score_features(f).lane in ("standard", "needs-CAB", "reject-back")


def test_f3_risky_looking_but_safe_scores_low():
    # low-criticality CI, business hours, tested rollback, clean requester
    c = cr(ci="cms-web", scheduled_at="2025-04-02T11:00:00", rollback_plan_present=True,
           rollback_plan_tested=True, test_evidence=True, requester="brand-new-eng")
    f = build_features(c, [])
    a = score_features(f)
    assert a.lane == "standard"


def test_f4_invented_reason_caught(history):
    c = cr()
    a = score_features(build_features(c, history))
    ev = build_evidence(c, a, [], [])
    expl = Explanation(change_id=c.id, lane=a.lane, summary="x",
                       claims=[ExplanationClaim(text="Vendor advisory V-777 says orders-db will fail",
                                                evidence_ids=["EV-CMDB"])])
    v = check_grounding(expl, ev)
    # advisory id has no matching evidence ref -> violation
    assert not v.grounded


def test_f5_budget_exhausted_graph_fail_closed(monkeypatch, history):
    import changeguard.graph as g
    from changeguard.config import settings
    monkeypatch.setattr(g, "load_history", lambda p: history)
    old = settings.assessment_budget_usd
    settings.assessment_budget_usd = 0.0
    try:
        rec = g.run_to_interrupt(cr())
        assert rec.explanation is not None
        assert "budget exhausted" in rec.explanation.summary
        assert rec.decision == "pending"  # still needs human CAB
    finally:
        settings.assessment_budget_usd = old
        gateway.reset_budget()
