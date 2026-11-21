"""LangGraph-style flow as a tiny owned graph (no new deps).

collect -> retrieve -> features -> score -> explain -> critic -> interrupt(CAB) -> record
All LLM calls go through the mock gateway client.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from . import gateway
from . import store as store_mod
from .config import settings
from .critic import check_grounding
from .explain import build_evidence, to_explanation
from .features import build_features
from .history import load_history
from .models import AssessmentRecord, ChangeRequest
from .retrieval import linked_incidents, retrieve_similar
from .scoring import score_features


@dataclass
class GraphState:
    change: ChangeRequest
    history: list[Any] = field(default_factory=list)
    similar: list[Any] = field(default_factory=list)
    incidents: list[str] = field(default_factory=list)
    features: Any = None
    assessment: Any = None
    evidence: list[Any] = field(default_factory=list)
    explanation: Any = None
    critic: Any = None
    record_id: str = ""


Node = Callable[[GraphState], GraphState]


def n_collect(s: GraphState) -> GraphState:
    s.history = load_history(settings.data_path)
    return s


def n_retrieve(s: GraphState) -> GraphState:
    s.similar = retrieve_similar(s.change, s.history)
    s.incidents = linked_incidents(s.change, s.history)
    return s


def n_features(s: GraphState) -> GraphState:
    s.features = build_features(s.change, s.history)
    return s


def n_score(s: GraphState) -> GraphState:
    a = score_features(s.features)
    a.change_id = s.change.id
    s.assessment = a
    return s


def n_explain(s: GraphState) -> GraphState:
    sim_tuples = [(h.id, h.outcome, h.title) for h, _ in s.similar]
    s.evidence = build_evidence(s.change, s.assessment, sim_tuples, s.incidents)
    try:
        res = gateway.explain_change(s.assessment, s.evidence)
    except gateway.BudgetExhausted:
        # Fail-closed: no explanation -> CAB must review manually.
        from .models import Explanation
        s.explanation = Explanation(
            change_id=s.change.id, lane=s.assessment.lane,
            summary="Explanation unavailable (budget exhausted). Manual CAB review required.",
            confidence="LOW", model=settings.mock_model)
        return s
    s.explanation = to_explanation(s.change, s.assessment, s.evidence, res)
    return s


def n_critic(s: GraphState) -> GraphState:
    if s.explanation is not None:
        s.critic = check_grounding(s.explanation, s.evidence)
    return s


NODES: dict[str, Node] = {
    "collect": n_collect,
    "retrieve": n_retrieve,
    "features": n_features,
    "score": n_score,
    "explain": n_explain,
    "critic": n_critic,
}
ORDER = ["collect", "retrieve", "features", "score", "explain", "critic"]


def run_to_interrupt(cr: ChangeRequest) -> AssessmentRecord:
    """Run graph up to the CAB interrupt; store record as pending."""
    st = GraphState(change=cr)
    for name in ORDER:
        st = NODES[name](st)
    rec = AssessmentRecord(
        id=f"A-{uuid4().hex[:8]}",
        change=cr,
        features=st.features,
        assessment=st.assessment,
        evidence=st.evidence,
        similar=[{"id": h.id, "outcome": h.outcome, "title": h.title} for h, _ in st.similar],
        explanation=st.explanation,
        critic=st.critic,
        decision="pending",
    )
    store_mod.save(rec)
    return rec
