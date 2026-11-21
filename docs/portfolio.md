# Portfolio — P0–P6 (study projects, all synthetic Acme Retail Ltd data)

- **P0 TicketSort** (`../ticketsort`): L1 ticket triage API — classification + gateway basics.
- **P1 Retrieval**: hybrid search + RRF over knowledge base — reused in ChangeGuard `retrieval.py`.
- **P2 Evals**: AgentJudge-style harnesses + CI quality gates — reused in `scripts/evaluate.py`.
- **P3 MCP + mock-ITSM**: CMDB tools + approval-gated writes — reused in `cmdb.py` / `mcp_tools.py`.
- **P4 Graphs**: LangGraph collect→…→HITL patterns — reused as the owned tiny graph in `graph.py`.
- **P5 Gateway**: single LLM adapter, cost/latency accounting, budgets — reused in `gateway.py`.
- **P6 ChangeGuard** (this repo, flagship): change-risk investigator + CAB release gate —
  deterministic score, evidence-linked LLM explanation, critic, human approval, PIR evals.
