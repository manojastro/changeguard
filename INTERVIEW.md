# INTERVIEW (15 Q&As — draft answers, challenge me on each)

1. **Why rules for the score and an LLM for the explanation?** Rules are
   explainable per-driver, auditable in git, and work with 420 rows; the LLM
   only phrases evidence that code already gathered (ADR-001).
2. **Why precision/recall, not accuracy?** 27% bad rate + 10:1 FN:FP costs:
   accuracy rewards "always success". Recall measures catching risky changes.
3. **How did you choose the threshold? What does a false negative cost?**
   Fixed 35 a priori (recall ≥0.80 target); FN=10×FP by CAB-time vs incident
   reasoning — assumption, must be retuned with real costs. Sweep in README.
4. **How is this different from a normal CAB checklist?** Same checks, but
   every CR gets the full history search + scored evidence instead of whoever
   remembers; the decision stays human.
5. **What would change with real data? Worries?** Stale CMDB, gaming the
   weights, bias vs new teams, PIR label leakage; fit a challenger model and
   A/B on recall-at-fixed-precision; quarterly threshold review.
6. **How does this reuse P0–P6?** See README reuse map (P1 RRF … P5 gateway).
7. **Why split train/test by time?** Random split leaks the future — a model
   tuned on March data tested on January data is cheating; CAB lives in the present.
8. **What does the critic actually check?** Every claim cites known evidence
   ids; any mentioned CI/change/incident id must have a matching evidence ref.
9. **What happens when the CMDB entry is missing?** Fail closed: criticality 10,
   high lane, CAB must review (F1) — never fail open.
10. **What if the gateway budget is exhausted?** Record stays pending with a
    LOW-confidence "manual review" note (F5).
11. **Why does the baseline have higher precision?** Flagging only critical CIs
    is conservative; we trade precision for recall deliberately (fail-closed).
12. **How do you know the LLM isn't inventing reasons?** Grounding rate metric
    (1.0 on test set) + critic unit tests with invented-reason fixtures (F4).
13. **Cost/latency per CR?** $0.00054 / 5.5ms mock; SLOs <$0.05 / <2s for a real
    provider — verify prices before prod.
14. **How would you roll back a bad rules release?** Revert weights commit,
    re-run evaluate.py; CI gate (recall ≥0.60) blocks bad merges anyway.
15. **Resume bullet?** "Built ChangeGuard (synthetic): recall 0.806 at precision
    0.341 vs baseline 0.389/0.412 on a time-split set of 126 changes, cost 126
    vs 240 at 10:1 FN:FP." (months of AI experience separate from 8.5y IT ops.)
