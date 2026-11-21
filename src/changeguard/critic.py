"""Critic: every explanation claim must be grounded in evidence ids (code).

Catches invented reasons (failure demo F4): any claim citing an unknown
evidence id, or mentioning a CI/change id with no matching evidence ref,
is a violation. Also flags empty-evidence claims.
"""

from __future__ import annotations

import re

from .models import CriticVerdict, Evidence, Explanation

_ID_RE = re.compile(r"\b(CR-\d+|CH-\d+|INC-\d+|[a-z]+-[a-z0-9-]+)\b", re.IGNORECASE)


def check_grounding(expl: Explanation, evidence: list[Evidence]) -> CriticVerdict:
    valid_ids = {e.id for e in evidence}
    refs = {e.ref for e in evidence} | {e.id for e in evidence}
    violations: list[str] = []
    grounded = 0
    for i, claim in enumerate(expl.claims):
        bad_ids = [eid for eid in claim.evidence_ids if eid not in valid_ids]
        if not claim.evidence_ids:
            violations.append(f"claim {i} has no evidence ids")
            continue
        if bad_ids:
            violations.append(f"claim {i} cites unknown evidence {bad_ids}")
            continue
        mentioned = set(_ID_RE.findall(claim.text))
        unknown = {m for m in mentioned if m not in refs and m.lower() not in {"lane", "top"}}
        # only flag tokens that look like ids (contain digit or dash-ci)
        unknown = {m for m in unknown if any(ch.isdigit() for ch in m)}
        if unknown:
            violations.append(f"claim {i} mentions unevidenced ids {sorted(unknown)}")
            continue
        grounded += 1
    rate = (grounded / len(expl.claims)) if expl.claims else 1.0
    return CriticVerdict(grounded=not violations, violations=violations,
                         grounding_rate=round(rate, 3))
