# LEARNING_LOG (auto-build mode: interfaces+impl shipped together, offline slice)

## M1 — Requirements & design — 2026-09-18
**Built:** docs/requirements.md, docs/design.md, ADR-001/002/003.
**New concepts:** deterministic-vs-LLM split (code decides, LLM explains);
SLOs on the gate itself; fail-closed defaults.
**Break-it result:** n/a (docs).
**Quiz:** n/a — auto-build.
**Interview line I can now say:** "Rules for the score, LLM for the explanation — auditability with 420 rows."

## M2 — Data — 2026-09-18
**Built:** scripts/generate_history.py (400 + 20 hand, hidden logit rules + noise).
**New concepts:** time-split (no peeking at the future); hidden rules + noise keep evals honest.
**Break-it result:** first run bad-rate 0.65 → retuned intercept −2.2 → −4.2 → 0.27 (DORA-plausible).
**Interview line I can now say:** "Random splits leak the future; we split by scheduled date."

## M3–M5 — Retrieval, features, score, explain, critic — 2026-09-18
**Built:** retrieval.py (hash-embed + keyword + RRF), features.py (9), scoring.py
(weighted lanes), gateway.py (mock + budgets), explain.py, critic.py.
**New concepts:** RRF fusion; grounding check as code; per-assessment cost caps.
**Break-it result:** predicted critic catches invented ids — actual: yes (F4 green).
**Interview line I can now say:** "Every LLM claim must cite an evidence id the code issued."

## M6–M7 — Graph, MCP, UI — 2026-09-18
**Built:** graph.py (own tiny graph + CAB interrupt), mcp_tools.py
(approval-gated write), api.py (one-page UI + 5 endpoints).
**New concepts:** interrupt = persist pending record; writes need approved=True.
**Interview line I can now say:** "The graph stops at the human; nothing writes without the CAB click."

## M8 — Eval — 2026-09-18
**Built:** scripts/evaluate.py → reports/eval.json.
**Measured:** P 0.341 / R 0.806 / F1 0.479 vs baseline 0.412/0.389/0.400;
cost 126 vs 240; grounding 1.0; $0.00054/CR; 5.5ms/CR.
**New concepts:** threshold from costs (10:1 FN:FP); recall matters more than precision here.
**Interview line I can now say:** "We trade precision for recall on purpose — missing a risky change costs 10× a false alarm."

## M9–M10 — Failures, runbook, gate — 2026-09-18
**Built:** docs/failures.md (5 demos as tests), docs/runbook.md, CI eval gate (recall ≥ 0.60).
**Interview line I can now say:** "Unknown CMDB entries fail closed, never open."
