"""AgentJudge-style eval: prediction (lane) vs outcome on the TIME-based test set.

Metrics: precision/recall/F1 (high-risk vs bad outcome), confusion matrix,
cost view (FN vs FP with justification), grounding rate, $/latency per CR,
baseline comparison (flag every change touching a critical CI).

Usage: uv run python scripts/evaluate.py [--gate-recall 0.60]
Writes reports/eval.json + reports/eval.md. Regenerates data if missing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from changeguard import gateway  # noqa: E402
from changeguard.cmdb import criticality  # noqa: E402
from changeguard.config import settings  # noqa: E402
from changeguard.critic import check_grounding  # noqa: E402
from changeguard.explain import build_evidence, to_explanation  # noqa: E402
from changeguard.features import build_features  # noqa: E402
from changeguard.history import load_history  # noqa: E402
from changeguard.models import BAD_OUTCOMES, ChangeRequest  # noqa: E402
from changeguard.retrieval import linked_incidents, retrieve_similar  # noqa: E402
from changeguard.scoring import is_high_risk, score_features  # noqa: E402

COST_JUSTIFICATION = (
    "A missed risky change (false negative) can cause a customer-facing incident "
    "or rollback: bridge calls, SLA breach, fix-forward work. A false alarm (false "
    "positive) costs one CAB review (~15 min). Relative cost FN:FP = 10:1 is an "
    "assumption — tune with real incident cost data."
)


def ensure_data() -> None:
    if not Path(settings.data_path).exists() or not Path(settings.data_path).read_text(encoding="utf-8").strip():
        subprocess.run([sys.executable, "scripts/generate_history.py"], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-recall", type=float, default=None)
    ap.add_argument("--split", type=float, default=0.7)
    args = ap.parse_args()

    ensure_data()
    hist = load_history(settings.data_path)
    cut = int(len(hist) * args.split)
    train, test = hist[:cut], hist[cut:]
    gateway.reset_budget()

    tp = fp = tn = fn = 0
    btp = bfp = btn = bfn = 0  # baseline
    total_cost = 0.0
    total_ms = 0
    grounded = 0
    claims = 0
    details = []
    for h in test:
        cr = ChangeRequest(**{k: v for k, v in h.model_dump().items() if k != "outcome"})
        feats = build_features(cr, train)
        a = score_features(feats)
        a.change_id = cr.id
        pred = is_high_risk(a)
        actual = h.outcome in BAD_OUTCOMES
        tp += pred and actual
        fp += pred and not actual
        tn += (not pred) and (not actual)
        fn += (not pred) and actual
        # baseline: flag critical CI (criticality >= 9)
        try:
            bpred = criticality(cr.ci) >= 9
        except KeyError:
            bpred = True
        btp += bpred and actual
        bfp += bpred and not actual
        btn += (not bpred) and (not actual)
        bfn += (not bpred) and actual

        sims = retrieve_similar(cr, train)
        ev = build_evidence(cr, a, [(s.id, s.outcome, s.title) for s, _ in sims],
                            linked_incidents(cr, train))
        t0 = time.monotonic()
        try:
            res = gateway.explain_change(a, ev)
            expl = to_explanation(cr, a, ev, res)
            total_cost += res.cost_usd
            total_ms += res.latency_ms
        except gateway.BudgetExhausted:
            from changeguard.models import Explanation
            expl = Explanation(change_id=cr.id, lane=a.lane,
                               summary="budget exhausted", confidence="LOW")
        total_ms += int((time.monotonic() - t0) * 1000)
        v = check_grounding(expl, ev)
        grounded += sum(1 for c in expl.claims) if v.grounded else int(v.grounding_rate * len(expl.claims))
        claims += len(expl.claims)
        details.append({"id": h.id, "pred": pred, "actual": actual, "lane": a.lane,
                        "score": a.score, "outcome": h.outcome})

    def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        return round(p, 3), round(r, 3), round(f, 3)

    p, r, f = prf(tp, fp, fn)
    bp, br, bf = prf(btp, bfp, bfn)
    n = len(test)
    report = {
        "n_test": n,
        "n_train": len(train),
        "model": {"precision": p, "recall": r, "f1": f,
                  "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}},
        "baseline_flag_critical_ci": {"precision": bp, "recall": br, "f1": bf,
                                      "confusion": {"tp": btp, "fp": bfp, "tn": btn, "fn": bfn}},
        "cost_view": {"fn_cost": settings.fn_cost, "fp_cost": settings.fp_cost,
                      "model_cost": round(fn * settings.fn_cost + fp * settings.fp_cost, 1),
                      "baseline_cost": round(bfn * settings.fn_cost + bfp * settings.fp_cost, 1),
                      "justification": COST_JUSTIFICATION},
        "grounding_rate": round(grounded / claims, 3) if claims else 1.0,
        "avg_cost_usd_per_cr": round(total_cost / n, 6) if n else 0.0,
        "avg_latency_ms_per_cr": round(total_ms / n, 1) if n else 0.0,
        "thresholds": {"high_risk": settings.high_risk_threshold, "reject": settings.reject_threshold},
        "slo": {"latency_ms_target": 2000, "cost_usd_target": 0.05,
                "latency_ok": (total_ms / n) < 2000 if n else True,
                "cost_ok": (total_cost / n) < 0.05 if n else True},
    }
    Path("reports").mkdir(exist_ok=True)
    (Path("reports/eval.json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
    (Path("reports/eval.md")).write_text(
        "# ChangeGuard eval (time-split test set)\n\n"
        f"test n={n} train n={len(train)}\n\n"
        f"| system | precision | recall | F1 | TP/FP/TN/FN |\n|---|---|---|---|---|\n"
        f"| changeguard | {p} | {r} | {f} | {tp}/{fp}/{tn}/{fn} |\n"
        f"| baseline (flag critical CI) | {bp} | {br} | {bf} | {btp}/{bfp}/{btn}/{bfn} |\n\n"
        f"cost: model {report['cost_view']['model_cost']} vs baseline {report['cost_view']['baseline_cost']} "
        f"(FN={settings.fn_cost}, FP={settings.fp_cost})\n\n"
        f"grounding {report['grounding_rate']} · ${report['avg_cost_usd_per_cr']}/CR · "
        f"{report['avg_latency_ms_per_cr']}ms/CR\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if args.gate_recall is not None and r < args.gate_recall:
        print(f"EVAL GATE FAILED: recall {r} < {args.gate_recall}")
        sys.exit(1)
    print(f"EVAL GATE PASSED: recall {r} >= {args.gate_recall}" if args.gate_recall else "eval done")


if __name__ == "__main__":
    main()
