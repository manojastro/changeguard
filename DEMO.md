# DEMO (2 minutes)

0:00 — "CAB reviews are inconsistent — they depend on who's on shift. ChangeGuard
does the investigation; humans still decide."
0:20 — Open `/`, assess the prefilled orders-db change → `/view/{id}`: lane +
score breakdown per driver, similar past changes, evidence ids.
0:50 — Point at explanation claims + mitigations, critic verdict grounded.
1:10 — Click request-info ("attach rollback test"), then approve; show decision
recorded via approval-gated write-back.
1:30 — Record PIR outcome; show `reports/eval.md`: recall 0.806 vs baseline
0.389, cost 126 vs 240 on the time-split test set.
1:50 — "Limits: synthetic data, templated explanations — the score is rules,
the LLM only explains, and every claim is grounding-checked."
