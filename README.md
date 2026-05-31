# Munshi

A testbed for Indian bureaucratic agentic workflows.

High-fidelity simulations of Indian government workflows — every tool, rule, and failure mode sourced from real audits. You bring an agent; Munshi runs it, scores it, and gives you a full trace.

**Live:** https://munshi-alpha.vercel.app/

---

## How it works

1. **World** — a simulation of one procedural domain. Typed MCP tools, enforced rules, failure modes from real audit records.
2. **Connect** — your agent connects over MCP (SSE or stdio). Any framework.
3. **Investigate** — the agent calls tools to probe world state: query records, verify identities, cross-check entitlements.
4. **Decide** — the agent acts. No guardrails. It owns the outcome.
5. **World enforces** — every action passes through the rule engine. Violations are caught and returned as structured rule codes.
6. **Score** — three axes: goal reached, rules upheld, cost used. Full replayable trace.

---

## Architecture

- **`worlds/<name>/`** — a self-contained world bundle: schemas, tools, rules, scorers, scenarios, seed data. Portable. Addable without touching anything else.
- **`backend/`** — FastAPI server. Exposes the world over MCP at `/mcp/<world>/sse`. Per-connection world isolation.
- **`agents/`** — reference agents shipped with the UP pension world: single ReAct, parallel per-case, compliance-layered.
- **`frontend/`** — static site (Vercel). Live workbench, scenario browser, leaderboard, trace replay.

---

## World: UP Pension Disbursement

Vridha · Vidhwa · Divyang schemes. 8 tools, 10 rules, 25 benchmark cases.

Failure modes modeled from CAG Report No. 10 of 2023, SIT Chitrakoot, and UIDAI/PFMS/NPCI documentation:

- Ghost pensioners (deceased, UIDAI death-flagged)
- Biometric mismatch (AePS fraud vector)
- NPCI mapper diverged or inactive
- Silent account swap after recent account change
- Life certificate expired or missing
- Name mismatch between PPO and Aadhaar record
- Invalid or unlinked Aadhaar

---

## Stack

| Layer | Choice |
|---|---|
| World tools | FastMCP |
| Schemas | Pydantic v2 |
| API | FastAPI + uvicorn |
| Reference agent | LangGraph + Claude Sonnet 4.6 |
| Frontend | Vanilla JS + Tailwind CDN |
| Deploy | EC2 (backend) · Vercel (frontend) |

---

## Running locally

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-...

# start the backend
uvicorn backend.main:app --reload

# run a reference agent
python -m agents.single
```

---

## Worlds in scope

- UP Property Registration
- GST Filing
- Passport Renewal
- FASTag Dispute
- Scholarship Disbursement
- Ration Card Update
