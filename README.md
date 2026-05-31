# Munshi

A benchmark for Indian bureaucratic agentic workflows.

High-fidelity simulations of Indian government workflows — every tool, rule, and failure mode sourced from real audits. You bring an agent; Munshi runs it, scores it, and gives you a full trace.

Munshi is the benchmark teams use before they sell systems to government. Same world, same cases, same scoring, same replay. A public leaderboard compares agents on completion, compliance, and cost.

**Live:** https://munshi-alpha.vercel.app/

---

## How it works

1. **Seed scenario** — a benchmark case loads a fresh world state.
2. **Connect agent** — your system binds over MCP (SSE or stdio). Any framework.
3. **Run tools** — the agent queries records, verifies identities, cross-checks entitlements, and decides what to do.
4. **Enforce rules** — the world checks every action server-side and returns structured rule violations when needed.
5. **Score the run** — completion, compliance, and cost are measured independently.
6. **Publish replay** — the run lands on the public leaderboard with a full trace.

Pipeline: `Scenario -> Fresh world -> Agent via MCP -> Rule enforcement -> Scoring -> Replay`

## Benchmark

Munshi is built for one thing: comparing bureaucratic agents on the same world under the same conditions.

- **Completion** — did the agent solve the cases?
- **Compliance** — did it stay inside the rules?
- **Cost** — how much did it spend to get there?

The leaderboard makes the comparison public. That is the point of the product: teams should be able to test their systems against Munshi before shipping to government.

---

## Architecture

- **`worlds/<name>/`** — a self-contained world bundle: schemas, tools, rules, scorers, scenarios, seed data. Portable. Addable without touching anything else.
- **`backend/`** — FastAPI server. Exposes the world over MCP at `/mcp/<world>/sse`. Per-connection world isolation.
- **`agents/`** — reference agents shipped with the UP pension world: single ReAct, parallel per-case, compliance-layered.
- **`frontend/`** — static site (Vercel). Live workbench, scenario browser, public leaderboard, trace replay.

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
