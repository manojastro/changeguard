"""LLM explanation wrapper: builds evidence, calls gateway, parses claims."""

from __future__ import annotations

from .gateway import GatewayResult
from .models import ChangeRequest, Evidence, Explanation, ExplanationClaim, RiskAssessment


def build_evidence(
    cr: ChangeRequest,
    assessment: RiskAssessment,
    similar: list[tuple[str, str, str]],
    incidents: list[str],
) -> list[Evidence]:
    ev: list[Evidence] = []
    f = assessment.features
    ev.append(Evidence(id="EV-CMDB", kind="cmdb", ref=cr.ci,
                       snippet=f"Touches {cr.ci}; blast radius {f.blast_radius_size} CIs.",
                       confidence="HIGH"))
    ev.append(Evidence(id="EV-FEAT", kind="feature", ref=cr.id,
                       snippet=(f"collisions={f.collision_count} freeze={f.freeze_window} "
                                f"rollback={f.rollback_present}/{f.rollback_tested} "
                                f"past_fail={f.past_failure_rate:.2f} "
                                f"window={f.window_risk:.2f} "
                                f"requester_fail={f.requester_fail_rate:.2f} "
                                f"tests={f.test_evidence}"),
                       confidence="HIGH"))
    for i, (cid, outcome, snippet) in enumerate(similar):
        ev.append(Evidence(id=f"EV-SIM-{i+1}", kind="past-change", ref=cid,
                           snippet=f"{cid} -> {outcome}: {snippet}", confidence="MEDIUM"))
    for i, inc in enumerate(incidents):
        ev.append(Evidence(id=f"EV-INC-{i+1}", kind="incident", ref=inc,
                           snippet=f"Linked incident {inc}.", confidence="MEDIUM"))
    return ev


def to_explanation(
    cr: ChangeRequest, assessment: RiskAssessment, evidence: list[Evidence], res: GatewayResult
) -> Explanation:
    ids = [e.id for e in evidence]
    claims = [
        ExplanationClaim(
            text=f"Lane is {assessment.lane} with score {assessment.score}.",
            evidence_ids=["EV-FEAT"],
            confidence="HIGH",
        ),
        ExplanationClaim(
            text=f"Top drivers: {', '.join(assessment.drivers) or 'none'}.",
            evidence_ids=["EV-FEAT", "EV-CMDB"],
            confidence="HIGH",
        ),
    ]
    if any(e.id.startswith("EV-SIM") for e in evidence):
        sim_ids = [i for i in ids if i.startswith("EV-SIM")]
        claims.append(ExplanationClaim(
            text="Similar past changes show elevated failure rate.",
            evidence_ids=sim_ids, confidence="MEDIUM"))
    mitigations = []
    f = assessment.features
    if not f.rollback_present:
        mitigations.append("Add a rollback plan before CAB.")
    elif not f.rollback_tested:
        mitigations.append("Test the rollback plan (game-day or restore rehearsal).")
    if f.freeze_window:
        mitigations.append("Move out of the freeze window or get freeze-exception sign-off.")
    if f.collision_count:
        mitigations.append("Reschedule away from colliding changes (±2h).")
    if not f.test_evidence:
        mitigations.append("Attach test evidence (staging pass / canary result).")
    mitigations.append("CAB reviewer to confirm blast-radius comms.")
    return Explanation(
        change_id=cr.id, lane=assessment.lane, summary=res.text.splitlines()[0],
        claims=claims, mitigations=mitigations, confidence="MEDIUM",
        model=res.model, latency_ms=res.latency_ms, cost_usd=res.cost_usd,
    )
