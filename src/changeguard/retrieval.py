"""Similar-past-changes hybrid mock retrieval.

embed = hashed token vector (deterministic, offline). keyword = token
overlap. Fusion = RRF over the two rankings. Same-CI / dependent-CI
filter applied first (P1 pattern reuse note: hybrid + RRF).
"""

from __future__ import annotations

import hashlib
import re
from math import sqrt

from .cmdb import blast_radius
from .models import ChangeRequest, HistoricalChange

_WS = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> set[str]:
    return set(_WS.findall(text.lower()))


def mock_embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic hash embedding: token hashes folded into `dim` buckets."""
    vec = [0.0] * dim
    for tok in tokens(text):
        h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    n = sqrt(sum(v * v for v in vec)) or 1.0
    return [v / n for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def keyword_overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def rrf_fuse(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal-rank fuse multiple id rankings into (id, score) desc."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def _in_scope(cr: ChangeRequest, h: HistoricalChange) -> bool:
    try:
        scope = set(blast_radius(cr.ci))
    except KeyError:
        return h.ci == cr.ci
    return h.ci in scope or cr.ci in _safe_blast(h.ci)


def _safe_blast(ci: str) -> set[str]:
    try:
        return set(blast_radius(ci))
    except KeyError:
        return {ci}


def retrieve_similar(
    cr: ChangeRequest,
    history: list[HistoricalChange],
    top_k: int = 5,
) -> list[tuple[HistoricalChange, float]]:
    """Hybrid (embed cosine + keyword) with RRF; CI-scope filter first."""
    cands = [h for h in history if h.id != cr.id and _in_scope(cr, h)]
    if not cands:
        cands = [h for h in history if h.id != cr.id]
    q_text = f"{cr.title} {cr.description} {cr.ci} {cr.change_type}"
    q_vec = mock_embed(q_text)
    q_tok = tokens(q_text)
    def emb_key(h: HistoricalChange) -> float:
        txt = f"{h.title} {h.description} {h.ci} {h.change_type}"
        return cosine(q_vec, mock_embed(txt))

    emb_ranked = sorted(cands, key=emb_key, reverse=True)
    kw_ranked = sorted(
        cands,
        key=lambda h: keyword_overlap(q_tok, tokens(f"{h.title} {h.description} {h.ci}")),
        reverse=True,
    )
    fused = dict(rrf_fuse([[h.id for h in emb_ranked], [h.id for h in kw_ranked]]))
    ordered = sorted(cands, key=lambda h: fused.get(h.id, 0.0), reverse=True)
    return [(h, fused.get(h.id, 0.0)) for h in ordered[:top_k]]


def linked_incidents(cr: ChangeRequest, history: list[HistoricalChange]) -> list[str]:
    out: list[str] = []
    for h in history:
        if h.outcome == "caused-incident" and (h.ci == cr.ci or h.id in cr.linked_incidents):
            out.extend(h.linked_incidents)
    seen = list(dict.fromkeys(out))
    return seen[:10]
