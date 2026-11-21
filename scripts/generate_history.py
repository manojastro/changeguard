"""Generate synthetic Acme change history with HIDDEN outcome rules + noise.

Hidden rules (learner-defined, from CAB experience — synthetic):
  logit = -2.2 + 0.12*blast + 0.18*crit + 0.50*collisions(+-2h)
          + 1.20*freeze + 1.10*no_rollback + 0.50*untested_rollback
          + 0.70*offhours + 1.60*requester_propensity + 0.80*no_tests
          + noise(0, 0.6);  p(bad) = sigmoid(logit). Intercept tuned so the
  marginal bad-outcome rate lands near 0.30 (DORA-plausible for a mixed
  normal/emergency change mix).
Bad outcomes split: failed 45% / caused-incident 30% / rolled-back 25%.
Time range 2024-06-01..2025-06-01. Split BY TIME downstream (no peeking).

Usage: uv run python scripts/generate_history.py [--n 400] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "src")
from changeguard.cmdb import blast_radius, criticality  # noqa: E402

CIS = ["orders-db", "payments-api", "checkout-web", "inventory-svc",
       "search-svc", "reporting-etl", "cms-web"]
CI_W = [14, 12, 16, 16, 16, 13, 13]
REQUESTERS = [f"rel-eng-0{i}" for i in range(1, 6)] + ["dba-01", "dba-02", "netops-01", "app-07", "app-11"]
TITLES = [
    "Index rebuild on {ci}", "Schema migration {ci} v{n}", "Config rollout {ci}",
    "Patch {ci} to {v}", "Scale-out {ci} workers", "TLS rotation {ci}",
    "Feature flag enablement {ci}", "Failover drill {ci}", "Cache policy change {ci}",
    "Deploy release {v} to {ci}",
]
DESCS = [
    "Routine maintenance with monitoring and staged rollout.",
    "Performance tuning; rollback steps documented and rehearsed.",
    "Security patch during reduced-traffic window with on-call cover.",
    "Capacity change ahead of peak; load test attached.",
    "Dependency upgrade; canary first then full fleet.",
]

FREEZE = (datetime(2024, 12, 20), datetime(2025, 1, 5))
OFF = set(range(0, 7)) | {22, 23}


def in_freeze(dt: datetime) -> bool:
    return FREEZE[0] <= dt <= FREEZE[1]


def offhours(dt: datetime) -> bool:
    return dt.hour in OFF or dt.weekday() >= 5


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    t0 = datetime(2024, 6, 1)
    span = (datetime(2025, 6, 1) - t0).total_seconds()
    prop = {r: rng.betavariate(2, 6) for r in REQUESTERS}  # hidden skill gaps

    base: list[dict] = []
    for i in range(args.n):
        ci = rng.choices(CIS, CI_W)[0]
        when = t0 + timedelta(seconds=rng.uniform(0, span))
        present = rng.random() < 0.68
        tested = bool(present and rng.random() < 0.5)
        base.append({
            "id": f"CH-{i+1:04d}",
            "title": rng.choice(TITLES).format(ci=ci, n=rng.randint(2, 9), v=f"1.{rng.randint(0,9)}.{rng.randint(0,9)}"),
            "description": rng.choice(DESCS),
            "ci": ci,
            "change_type": rng.choices(["normal", "standard", "emergency"], [70, 20, 10])[0],
            "scheduled_at": when,
            "requester": rng.choice(REQUESTERS),
            "rollback_plan_present": present,
            "rollback_plan_tested": tested,
            "test_evidence": rng.random() < 0.6,
        })
    # collisions are computed against the full set (same fn as features)
    times = sorted(b["scheduled_at"] for b in base)
    import bisect
    recs = []
    for b in base:
        lo = b["scheduled_at"] - timedelta(hours=2)
        hi = b["scheduled_at"] + timedelta(hours=2)
        coll = bisect.bisect_right(times, hi) - bisect.bisect_left(times, lo) - 1
        blast = len(blast_radius(b["ci"]))
        crit = criticality(b["ci"])
        logit = (-4.2 + 0.12 * blast + 0.18 * crit + 0.50 * min(coll, 4)
                 + 1.20 * in_freeze(b["scheduled_at"]) + 1.10 * (not b["rollback_plan_present"])
                 + 0.50 * (b["rollback_plan_present"] and not b["rollback_plan_tested"])
                 + 0.70 * offhours(b["scheduled_at"]) + 1.60 * prop[b["requester"]]
                 + 0.80 * (not b["test_evidence"]) + rng.gauss(0, 0.6))
        bad = rng.random() < sigmoid(logit)
        if bad:
            outcome = rng.choices(["failed", "caused-incident", "rolled-back"], [45, 30, 25])[0]
        else:
            outcome = "success"
        inc = [f"INC-{rng.randint(1000,9999)}"] if outcome == "caused-incident" else []
        if outcome == "failed" and rng.random() < 0.2:
            inc = [f"INC-{rng.randint(1000,9999)}"]
        recs.append({**b, "scheduled_at": b["scheduled_at"].isoformat(),
                     "outcome": outcome, "blast_radius": blast, "linked_incidents": inc})
    recs.sort(key=lambda r: r["scheduled_at"])
    data = Path("data")
    data.mkdir(exist_ok=True)
    (data / "history.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")

    # 20 hand-written edge cases (anonymised, synthetic)
    hand = [
        ("H-01", "Freeze-week deploy of checkout-web promo flag", "checkout-web", "2024-12-23T10:00:00", "rel-eng-01", True, True, True, "normal"),
        ("H-02", "orders-db emergency fix, no rollback possible", "orders-db", "2025-02-11T03:10:00", "dba-01", False, False, False, "emergency"),
        ("H-03", "cms-web copy change, fully tested", "cms-web", "2025-04-02T11:00:00", "app-11", True, True, True, "standard"),
        ("H-04", "payments-api TLS rotation with rehearsed rollback", "payments-api", "2025-01-15T14:00:00", "rel-eng-02", True, True, True, "normal"),
        ("H-05", "inventory-svc weekend scale-out, no tests", "inventory-svc", "2025-05-17T23:30:00", "app-07", True, False, False, "normal"),
        ("H-06", "reporting-etl backfill, low risk weekday", "reporting-etl", "2025-03-05T10:00:00", "app-11", True, True, True, "standard"),
        ("H-07", "search-svc cache policy, colliding deploy window", "search-svc", "2025-03-05T10:30:00", "rel-eng-03", False, False, True, "normal"),
        ("H-08", "checkout-web flag, senior requester clean record", "checkout-web", "2025-04-22T13:00:00", "rel-eng-01", True, True, True, "normal"),
        ("H-09", "orders-db index rebuild off-hours tested", "orders-db", "2025-03-14T22:30:00", "dba-02", True, True, True, "normal"),
        ("H-10", "payments-api config, repeat requester with failures", "payments-api", "2025-05-02T21:00:00", "app-07", False, False, False, "normal"),
        ("H-11", "cms-web theme deploy", "cms-web", "2025-02-04T15:00:00", "app-11", True, False, True, "standard"),
        ("H-12", "inventory-svc schema migration freeze edge", "inventory-svc", "2025-01-04T23:00:00", "rel-eng-04", True, False, False, "normal"),
        ("H-13", "search-svc synonym update business hours", "search-svc", "2025-04-09T10:00:00", "rel-eng-03", True, True, True, "standard"),
        ("H-14", "reporting-etl partition change, no rollback", "reporting-etl", "2025-05-28T02:00:00", "netops-01", False, False, False, "normal"),
        ("H-15", "checkout-web emergency hotfix noon", "checkout-web", "2025-02-19T12:00:00", "rel-eng-02", False, False, True, "emergency"),
        ("H-16", "orders-db stats update, tested rollback", "orders-db", "2025-04-30T03:00:00", "dba-01", True, True, True, "normal"),
        ("H-17", "payments-api SDK bump, full evidence", "payments-api", "2025-05-20T11:00:00", "rel-eng-01", True, True, True, "normal"),
        ("H-18", "inventory-svc worker scale, untested rollback", "inventory-svc", "2025-03-19T01:30:00", "app-07", True, False, True, "normal"),
        ("H-19", "cms-web redirect map, trivial", "cms-web", "2025-05-06T09:30:00", "app-11", True, True, True, "standard"),
        ("H-20", "search-svc reindex, freeze + off-hours", "search-svc", "2024-12-27T01:00:00", "rel-eng-05", False, False, False, "normal"),
    ]
    # label hand outcomes with the same hidden rule (deterministic-ish, seed 7)
    hrng = random.Random(7)
    hand_recs = []
    for hid, title, ci, when_s, req, pres, tested, tests, ctype in hand:
        when = datetime.fromisoformat(when_s)
        coll = sum(1 for r in recs
                   if abs((datetime.fromisoformat(r["scheduled_at"]) - when).total_seconds()) <= 7200)
        logit = (-4.2 + 0.12 * len(blast_radius(ci)) + 0.18 * criticality(ci) + 0.50 * min(coll, 4)
                 + 1.20 * in_freeze(when) + 1.10 * (not pres) + 0.50 * (pres and not tested)
                 + 0.70 * offhours(when) + 1.60 * prop.get(req, 0.2) + 0.80 * (not tests))
        bad = hrng.random() < sigmoid(logit)
        outcome = hrng.choices(["failed", "caused-incident", "rolled-back"], [45, 30, 25])[0] if bad else "success"
        hand_recs.append({"id": hid, "title": title, "description": "Hand-written CAB edge case (synthetic).",
                          "ci": ci, "change_type": ctype, "scheduled_at": when_s, "requester": req,
                          "rollback_plan_present": pres, "rollback_plan_tested": tested,
                          "test_evidence": tests, "outcome": outcome,
                          "blast_radius": len(blast_radius(ci)),
                          "linked_incidents": [f"INC-{hrng.randint(1000,9999)}"] if outcome == "caused-incident" else []})
    (data / "hand_changes.jsonl").write_text("\n".join(json.dumps(r) for r in hand_recs) + "\n", encoding="utf-8")
    # merge hand into history, keep time order
    merged = recs + hand_recs
    merged.sort(key=lambda r: r["scheduled_at"])
    (data / "history.jsonl").write_text("\n".join(json.dumps(r) for r in merged) + "\n", encoding="utf-8")
    bad_rate = sum(1 for r in merged if r["outcome"] != "success") / len(merged)
    print(f"wrote {len(merged)} changes ({args.n} generated + 20 hand), bad-outcome rate {bad_rate:.2f}")


if __name__ == "__main__":
    main()
