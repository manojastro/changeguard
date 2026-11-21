"""Pydantic v2 data shapes for ChangeGuard."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Outcome = Literal["success", "failed", "caused-incident", "rolled-back"]
Lane = Literal["standard", "needs-CAB", "reject-back"]
Decision = Literal["approved", "rejected", "needs-info", "pending"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]
BAD_OUTCOMES: frozenset[str] = frozenset({"failed", "caused-incident", "rolled-back"})


class ChangeRequest(BaseModel):
    id: str
    title: str
    description: str
    ci: str
    change_type: Literal["normal", "standard", "emergency"]
    scheduled_at: datetime
    requester: str
    rollback_plan_present: bool = False
    rollback_plan_tested: bool = False
    test_evidence: bool = False
    linked_incidents: list[str] = Field(default_factory=list)


class HistoricalChange(ChangeRequest):
    outcome: Outcome
    blast_radius: int = 1


class RiskFeatures(BaseModel):
    blast_radius_size: int = Field(ge=0)
    ci_criticality: float = Field(ge=0, le=10)
    collision_count: int = Field(ge=0)
    freeze_window: bool = False
    rollback_present: bool = False
    rollback_tested: bool = False
    past_failure_rate: float = Field(ge=0, le=1)
    window_risk: float = Field(ge=0, le=1)
    requester_fail_rate: float = Field(ge=0, le=1)
    test_evidence: bool = False


class ScoreBreakdown(BaseModel):
    contributions: dict[str, float] = Field(default_factory=dict)
    threshold_standard: float = 35.0
    threshold_reject: float = 65.0


class RiskAssessment(BaseModel):
    change_id: str
    score: float = Field(ge=0, le=100)
    lane: Lane
    drivers: list[str] = Field(default_factory=list)
    features: RiskFeatures
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)


class Evidence(BaseModel):
    id: str
    kind: Literal["past-change", "incident", "cmdb", "schedule", "feature"]
    ref: str
    snippet: str
    confidence: Confidence = "MEDIUM"


class ExplanationClaim(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = "MEDIUM"


class Explanation(BaseModel):
    change_id: str
    lane: Lane
    summary: str
    claims: list[ExplanationClaim] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
    confidence: Confidence = "MEDIUM"
    model: str = "mock-explainer-1"
    latency_ms: int = 0
    cost_usd: float = 0.0


class CriticVerdict(BaseModel):
    grounded: bool
    violations: list[str] = Field(default_factory=list)
    grounding_rate: float = Field(ge=0, le=1, default=1.0)


class AssessmentRecord(BaseModel):
    id: str
    change: ChangeRequest
    features: RiskFeatures
    assessment: RiskAssessment
    evidence: list[Evidence] = Field(default_factory=list)
    similar: list[dict[str, str]] = Field(default_factory=list)
    explanation: Explanation | None = None
    critic: CriticVerdict | None = None
    decision: Decision = "pending"
    decision_comment: str = ""
    outcome: Outcome | None = None
