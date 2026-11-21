"""Mock LLM gateway client. All LLM calls go through here (P5 pattern).

Offline + deterministic: template rendering only, simulated latency/cost
from config/prices.yaml. Enforces per-assessment budget (failure demo F5).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import settings
from .models import Evidence, RiskAssessment


def _prices() -> dict[str, float]:
    here = Path(__file__).resolve()
    for cand in [Path.cwd() / "config" / "prices.yaml",
                 here.parents[2] / "config" / "prices.yaml"]:
        if cand.exists():
            return dict(yaml.safe_load(cand.read_text(encoding="utf-8"))["mock"])
    raise FileNotFoundError("config/prices.yaml not found")


PRICES = _prices()

IN_PER_1K = float(PRICES["input_per_1k"])
OUT_PER_1K = float(PRICES["output_per_1k"])


class BudgetExhausted(RuntimeError):
    pass


@dataclass
class GatewayResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float


_spent_this_run: float = 0.0


def reset_budget() -> None:
    global _spent_this_run
    _spent_this_run = 0.0


def spent() -> float:
    return _spent_this_run


def explain_change(assessment: RiskAssessment, evidence: list[Evidence]) -> GatewayResult:
    """Render the deterministic explanation template via the mock gateway."""
    global _spent_this_run
    t0 = time.monotonic()
    ev_lines = "\n".join(f"- [{e.id}] ({e.kind}) {e.snippet}" for e in evidence)
    text = (
        f"Lane: {assessment.lane} (score {assessment.score}/100).\n"
        f"Top drivers: {', '.join(assessment.drivers) or 'none'}.\n"
        f"Evidence:\n{ev_lines}\n"
        f"Mitigations: add a tested rollback plan; move out of freeze/collision "
        f"windows; attach test evidence."
    )
    input_tokens = max(1, len(ev_lines.split()) + 120)
    output_tokens = max(1, len(text.split()))
    cost = input_tokens / 1000 * IN_PER_1K + output_tokens / 1000 * OUT_PER_1K
    if _spent_this_run + cost > settings.max_usd_per_run or cost > settings.assessment_budget_usd:
        raise BudgetExhausted(
            f"mock gateway budget exhausted: need ${cost:.4f}, "
            f"per-assessment cap ${settings.assessment_budget_usd}, "
            f"run cap ${settings.max_usd_per_run}"
        )
    _spent_this_run += cost
    latency_ms = int((time.monotonic() - t0) * 1000) + 5  # simulated floor
    return GatewayResult(
        text=text,
        model=settings.mock_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        cost_usd=round(cost, 6),
    )
