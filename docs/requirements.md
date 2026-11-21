# ChangeGuard — Requirements (synthetic Acme Retail Ltd)

## 1. Users
- **CAB reviewers / change managers**: decide approve / reject / request-info on normal changes.
- **Requesters (rel-eng, DBA, app teams)**: see why a change was flagged and what mitigation unblocks it.
- **Ops leadership**: cost-of-failure view; SLOs on the gate itself.

## 2. CAB process modelled (anonymised)
Normal change → reviewer checks: what does it touch (CMDB blast radius),
similar past changes + linked incidents, collisions in the change calendar
(±2h), freeze windows, rollback plan present AND tested, test evidence,
requester track record. Emergency changes skip the queue but are still scored.
Decision is always human; the tool only recommends a lane.

## 3. Inputs / outputs
- In: ChangeRequest (title, description, CI, type, schedule, requester, rollback/test flags).
- Out: RiskAssessment (score 0–100, lane standard/needs-CAB/reject-back, drivers,
  per-driver points), evidence list with ids, LLM explanation with confidence +
  mitigations, critic verdict, CAB decision, PIR outcome.

## 4. Deterministic vs LLM split
- **Code decides**: features, score, lane, grounding check, approval gating.
- **LLM explains**: lane summary, drivers phrased with evidence ids, mitigations.
  The LLM can never change the lane and every claim must cite evidence ids
  (critic enforces; violations fail closed to manual review).

## 5. Approvals
`add_change_note` (write-back) requires `approved=True` (the CAB click).
No autonomous writes. Budget exhaustion → explanation marked LOW confidence,
record stays `pending`, human must review.

## 6. Non-goals
No auto-approval, no real CMDB/ITSM integration, no ML model (ADR-001),
no PII, no real incident data (all synthetic).

## 7. SLOs (assumption — justify before prod)
- Assessment p95 < 2s (mock gateway; measure in reports/eval.json).
- Cost < $0.05 per CR (mock prices; verify on provider site before real LLM).
- Explanation grounding rate ≥ 0.90; recall on risky changes ≥ 0.60 (CI gate).
