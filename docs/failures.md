# Failure demos (all reproduced by `pytest tests/test_failures.py -v`)

## F1 — Missing CMDB data → fail closed, never fail open
Unknown CI (`ghost-ci-99`) raises KeyError in `cmdb`; `features` catches it,
assumes criticality 10 and still scores (lane needs-CAB/reject-back).
Repro: `pytest tests/test_failures.py::test_f1_missing_cmdb_fail_closed -v`

## F2 — Conflicting history (2 success / 2 bad) → honest 0.5 rate
`past_failure_rate` returns 0.5; score reflects uncertainty instead of hiding it.
Repro: `pytest tests/test_failures.py::test_f2_conflicting_history_still_scores -v`

## F3 — Risky-looking-but-safe (cms-web, business hours, tested) → standard
Low-criticality CI + clean signals scores <35 despite "deploy" wording that a
keyword-only gate would flag.
Repro: `pytest tests/test_failures.py::test_f3_risky_looking_but_safe_scores_low -v`

## F4 — Invented reason caught by critic
Claim citing unevidenced advisory/ids → `grounded=false` + violation listing
the unknown ids. In the graph path the record keeps the violation visible for CAB.
Repro: `pytest tests/test_failures.py::test_f4_invented_reason_caught -v`
(also `tests/test_explain_critic.py::test_critic_catches_invented_reason`)

## F5 — Gateway budget exhausted mid-assessment → fail closed to human
`assessment_budget_usd=0` forces `BudgetExhausted`; graph stores the record as
`pending` with a LOW-confidence "manual CAB review required" explanation.
Repro: `pytest tests/test_failures.py::test_f5_budget_exhausted_graph_fail_closed -v`
