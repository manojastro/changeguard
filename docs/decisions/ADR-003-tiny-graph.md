# ADR-003 — Owned tiny graph instead of LangGraph

Date: 2026-09-18 · Status: accepted

## Context
P6 brief says LangGraph-style flow; adding the dependency for a linear
7-node pipeline with one interrupt is heavy for an offline slice.

## Decision
`graph.py`: ORDER list + node functions + `run_to_interrupt` (interrupt =
persist `pending` record for CAB). Same node names as the P4 pattern so the
LangGraph port is mechanical.

## Consequences
- No checkpointing/durable interrupts (in-memory store) — noted in runbook.
- Port to LangGraph later without changing node logic or API.
