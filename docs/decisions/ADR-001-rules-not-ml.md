# ADR-001 — Rules (not ML) for the v1 risk score

Date: 2026-09-18 · Status: accepted

## Context
~420 synthetic changes, binary-ish bad outcome, need CAB trust + auditability.

## Decision
Weighted-rule `score(features)` with env-tunable thresholds. No trained model.

## Why
- Explainable: per-driver points shown in UI; an auditor can recompute by hand.
- Auditable: weights + thresholds in git; every change reviewed against eval gate.
- Little data: 420 rows cannot support a calibrated classifier; rules encode CAB experience directly.
- Reversible: if real data arrives, fit logistic regression on the same 9 features
  and A/B it against rules on recall-at-fixed-precision (see INTERVIEW.md Q5).

## Consequences
- Thresholds must be retuned with costs (10:1 FN:FP); CI gate guards recall.
- Rules go stale as systems change → quarterly review + PIR trend watch.
