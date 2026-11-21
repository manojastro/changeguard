# ChangeGuard runbook (for ChangeGuard itself)

## Alerts
- `eval_gate_failed`: CI `--gate-recall` tripped → freeze rules/prompt release, inspect reports/eval.md.
- `grounding_rate < 0.90` → explanation template regression; roll back prompt (see below).
- `p95_latency > 2s` / `cost_per_CR > $0.05` → check gateway mode/prices, traffic spike.
- `assessment errors > 1%` → likely CMDB load failure; assessments fail closed (high-risk) so CAB queue grows — page on-call.

## When it's down
1. CAB falls back to the manual checklist (requirements.md §2); the `/` page shows an error but decisions can be emailed.
2. `docker compose up --build` restores the stack; health at `GET /health`.
3. Pending records are in-memory in this slice (prod: DB) — re-POST assessments after restart.

## Rolling back a bad prompt/rules release
- Rules: revert `src/changeguard/scoring.py` WEIGHTS/thresholds commit, re-run `scripts/evaluate.py`.
- Prompt: template lives in `gateway.explain_change`; revert + check grounding rate.
- CI blocks merge if recall < 0.60 (`--gate-recall`).

## Data retention
Synthetic only. History JSONL + assessment records: keep 90 days in prod, then
aggregate to counts. No PII by construction (requesters are synthetic handles).

## Deploy notes (P5 reuse)
Same shape as P5: `Dockerfile` (non-root, healthcheck) + `compose.yml` behind
the gateway; env via `.env` (see `.env.example`); mock provider default so a
fresh clone runs offline: `docker compose up --build`.
