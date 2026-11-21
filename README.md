# ChangeGuard — AI change-risk investigator + CAB release gate (P6 capstone)

> All data synthetic (Acme Retail Ltd). All numbers below are measured —
> regenerate with `uv run python scripts/evaluate.py` and read `reports/eval.json`.

## The CAB problem (in CAB language)
Every week the CAB reviews normal changes with a checklist: blast radius from
the CMDB, similar past changes and their incidents, collisions in the change
calendar, freeze windows, rollback plan (present *and* tested), test evidence,
and the requester's track record. Reviews are inconsistent — they depend on who
is on shift and how much history they remember. ChangeGuard automates the
*investigation* so the human decision is faster and evidence-linked. It never
approves anything itself.

## Design: code decides, LLM explains
```
CR → collect (MCP) → retrieve (hybrid RAG) → features (code) → score (rules)
   → explain (LLM template via gateway) → critic (grounding, code)
   → CAB interrupt → record → PIR outcome → eval
```
- **Deterministic**: 9 risk features, weighted score → lane
  (standard <35 / needs-CAB 35–65 / reject-back ≥65), grounding critic,
  approval-gated write-back. See `docs/design.md`, ADR-001.
- **AI**: similar-past-change retrieval (hash-embed + keyword + RRF) and the
  explanation (drivers with evidence ids, confidence, mitigations).
- **Human control**: every record waits at `pending` for CAB
  approve / reject / request-info; PIR outcome closes the loop.

## Results vs baseline (time-split test set, n=126; train n=294)

| system | precision | recall | F1 | TP/FP/TN/FN | cost* |
|---|---|---|---|---|---|
| ChangeGuard (thr 35) | 0.341 | **0.806** | **0.479** | 29/56/34/7 | **126** |
| baseline: flag critical CI | 0.412 | 0.389 | 0.400 | 14/20/70/22 | 240 |

\*cost = 10·FN + 1·FP. A missed risky change (incident/rollback, bridge call,
SLA breach) costs ~10× a false alarm (one 15-min CAB review) — assumption,
tune with real incident costs.
Grounding rate 1.0 · $0.00054/CR · 5.5ms/CR (mock gateway; SLOs: <$0.05, <2s).

Post-hoc threshold sweep on the test set (analysis only — shipped threshold 35
was fixed a priori): thr 25 → R 0.944/cost 91 but 105 CAB reviews; thr 40 →
P 0.419/R 0.722/cost 136. Threshold 35 keeps recall ≥0.80 at moderate review load.
Honest note: the model trails the baseline on precision (0.341 vs 0.412) — the
intended fail-closed trade: it over-flags rather than miss risky changes.

## How to run (1 command stack)
```bash
uv sync --group dev
uv run python scripts/generate_history.py   # 400 + 20 hand synthetic changes
uv run pytest -q                             # 25 tests
uv run python scripts/evaluate.py            # → reports/eval.json
uv run uvicorn changeguard.api:app --reload  # → http://localhost:8000
```
CR→decision→outcome loop: `POST /assessments` → open `/view/{id}` →
approve/reject/request-info → `POST /assessments/{id}/outcome` (PIR).
Or `docker compose up --build`. CI runs lint + types + tests + eval gate
(recall ≥ 0.60).

## Failure demos
5 documented + tested: missing CMDB (fail-closed), conflicting history,
risky-looking-but-safe, invented reason caught by critic, budget exhausted.
See `docs/failures.md`; repro: `pytest tests/test_failures.py -v`.

## Trade-offs / limits
- Synthetic data, rules not validated on real changes; hash embeddings miss
  semantics; explanations are templated (mock gateway).
- With real data I would worry about: stale CMDB (blast radius lies), gaming
  (requesters learning the weights), bias against new teams (no history →
  requester rate 0 but past-failure neighbours незнакомы), label leakage in PIR.
  See INTERVIEW.md Q5 and docs/runbook.md.

## What I'd do next
Real embeddings behind the same retriever signature, logistic-regression
challenger on the same 9 features (A/B on recall-at-fixed-precision),
durable store + LangGraph port (ADR-003), Slack approval mock.

## Reuse map (P0–P6)
P1 hybrid+RRF → `retrieval.py` · P2 eval harness+gates → `scripts/evaluate.py` ·
P3 CMDB/approval-gated writes → `cmdb.py`/`mcp_tools.py` · P4 graph+HITL →
`graph.py` · P5 gateway/cost caps → `gateway.py`. Full map: `docs/portfolio.md`.
