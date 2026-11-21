# ADR-002 — Mock gateway + hash embeddings (offline-first slice)

Date: 2026-09-18 · Status: accepted

## Context
Must build and demo with no network, no API keys, no vector DB.

## Decision
- All LLM calls via `gateway.py` mock (deterministic template, token/cost accounting, budgets).
- Retrieval similarity via `mock_embed` (SHA-256 token buckets) + keyword Jaccard + RRF.

## Why
- Runs everywhere (`uv sync && pytest`), deterministic evals, zero cost.
- Single choke point: swapping `mock` → real provider touches one module.

## Consequences
- Explanations are templated (honest limit, see README).
- Hash embeddings miss semantics — fine for the synthetic slice; real slice would
  plug real embeddings behind the same `retrieve_similar` signature.
