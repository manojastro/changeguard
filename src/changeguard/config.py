"""Central settings. All tunables come from env — nothing hard-coded in logic."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "mock"
    mock_model: str = "mock-explainer-1"
    max_usd_per_run: float = 5.0
    assessment_budget_usd: float = 0.50
    high_risk_threshold: float = 35.0
    reject_threshold: float = 65.0
    fn_cost: float = 10.0
    fp_cost: float = 1.0
    data_path: str = "data/history.jsonl"
    hand_changes_path: str = "data/hand_changes.jsonl"
    request_id: str = "local"


settings = Settings()
