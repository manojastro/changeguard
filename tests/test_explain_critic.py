import pytest
from conftest import cr

from changeguard import gateway
from changeguard.config import settings
from changeguard.critic import check_grounding
from changeguard.explain import build_evidence, to_explanation
from changeguard.features import build_features
from changeguard.models import Explanation, ExplanationClaim
from changeguard.retrieval import linked_incidents, retrieve_similar
from changeguard.scoring import score_features


def test_explain_and_critic_grounded(history):
    c = cr()
    sims = retrieve_similar(c, history)
    a = score_features(build_features(c, history))
    ev = build_evidence(c, a, [(h.id, h.outcome, h.title) for h, _ in sims], linked_incidents(c, history))
    gateway.reset_budget()
    res = gateway.explain_change(a, ev)
    expl = to_explanation(c, a, ev, res)
    v = check_grounding(expl, ev)
    assert v.grounded, v.violations
    assert expl.cost_usd < settings.assessment_budget_usd


def test_critic_catches_invented_reason(history):
    c = cr()
    sims = retrieve_similar(c, history)
    a = score_features(build_features(c, history))
    ev = build_evidence(c, a, [(h.id, h.outcome, h.title) for h, _ in sims], [])
    expl = Explanation(change_id=c.id, lane=a.lane, summary="x",
                       claims=[ExplanationClaim(text="Caused by ghost-ci-99 failure CH-9999",
                                                evidence_ids=["EV-NOPE"])])
    v = check_grounding(expl, ev)
    assert not v.grounded and v.violations


def test_budget_exhausted():
    gateway.reset_budget()
    old = settings.assessment_budget_usd
    settings.assessment_budget_usd = 0.0
    try:
        from changeguard.models import Evidence, RiskAssessment, RiskFeatures
        a = RiskAssessment(change_id="x", score=90, lane="reject-back",
                           features=RiskFeatures(blast_radius_size=1, ci_criticality=1,
                                                 collision_count=0, freeze_window=False,
                                                 rollback_present=True, rollback_tested=True,
                                                 past_failure_rate=0.0, window_risk=0.0,
                                                 requester_fail_rate=0.0, test_evidence=True))
        with pytest.raises(gateway.BudgetExhausted):
            gateway.explain_change(a, [Evidence(id="E1", kind="feature", ref="x", snippet="s")])
    finally:
        settings.assessment_budget_usd = old
        gateway.reset_budget()
