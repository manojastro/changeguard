"""Mock CMDB (P3-style). Synthetic Acme Retail Ltd CIs with dependencies.

Blast radius = the CI itself + all transitive dependents (services that
depend on it). Missing CI -> KeyError, which the graph maps to a safe
high-risk assessment (see docs/failures.md F1).
"""

from __future__ import annotations

from typing import TypedDict


class CIRecord(TypedDict):
    criticality: int
    tier: str
    depends_on: list[str]


CIS: dict[str, CIRecord] = {
    "orders-db": {"criticality": 10, "tier": "critical", "depends_on": []},
    "payments-api": {"criticality": 10, "tier": "critical", "depends_on": ["orders-db"]},
    "checkout-web": {"criticality": 8, "tier": "high", "depends_on": ["payments-api", "orders-db"]},
    "inventory-svc": {"criticality": 7, "tier": "high", "depends_on": ["orders-db"]},
    "search-svc": {"criticality": 5, "tier": "medium", "depends_on": ["inventory-svc"]},
    "reporting-etl": {"criticality": 3, "tier": "low", "depends_on": ["orders-db", "inventory-svc"]},  # noqa: E501
    "cms-web": {"criticality": 2, "tier": "low", "depends_on": []},
}


def get_ci(name: str) -> CIRecord:
    """Return CI record or raise KeyError for unknown CI."""
    if name not in CIS:
        raise KeyError(f"unknown CI: {name}")
    return CIS[name]


def criticality(name: str) -> float:
    return float(get_ci(name)["criticality"])


def blast_radius(name: str) -> list[str]:
    """CI + transitive dependents. Raises KeyError if CI unknown."""
    get_ci(name)  # validate first
    dependents: dict[str, list[str]] = {ci: [] for ci in CIS}
    for ci, rec in CIS.items():
        for dep in rec["depends_on"]:
            dependents.setdefault(dep, []).append(ci)
    seen = {name}
    stack = [name]
    while stack:
        cur = stack.pop()
        for child in dependents.get(cur, []):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return sorted(seen)
