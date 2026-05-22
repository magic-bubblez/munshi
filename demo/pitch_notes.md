# Munshi Pitch Notes

A 60-90 second pitch script for the hackathon demo, plus the moments that land.

## The setup (15 seconds)

> "Multi-agent AI systems don't fail because the agents are bad — they fail because the *world they touch* breaks when multiple agents act on it. Every team building agentic systems for Indian government workflows ends up mocking the same broken APIs, writing the same scorers, badly, from scratch.
>
> Munshi is the shared substrate. One simulated world per government domain, your agent plugs in over MCP, you get a scoreboard and a replay trace."

## The demo (45 seconds)

> "Today's world: UP social pension disbursement. We modeled it from real CAG audits — the Chitrakoot Rs 43 crore scam, the Shahjahanpur Rs 2.52 crore scam, the famous ghost-pensioner problem. Eight tools, eight server-side rules, seven test pensioners.
>
> Watch the agent." *(run `./demo/run.sh` or click into the replay UI)*
>
> "Seven pensioners due this quarter. Two are clean. Five have anomalies that have cost the UP government crores. The agent handles all of them in 56 seconds for 15 cents."

## The moments to point at in the replay UI

1. **PPO-UP-VR-0001 / PPO-UP-VI-0007** — clean disbursements. The happy path works.
2. **PPO-UP-VI-0002 (Sushila Devi, ghost pensioner)** — the agent *tries* to disburse, the world rejects with `R-04-DEATH_FLAGGED`, the agent recovers by calling `flag_death_and_cancel`. That recovery loop is the testbed catching what production silently misses.
3. **PPO-UP-VR-0003 (Krishna Mishra, account swap)** — agent flags for audit, naming the "Shahjahanpur-type scam" pattern unprompted. Bank holder name "Anonymous Accomplice" was caught.
4. **PPO-UP-VR-0004 (Phoolmati, NPCI divergence)** — agent cites the DBT "last seeded wins" rule in its reasoning. This is the FM-06 misroute that drains accounts silently in production.
5. **PPO-UP-DI-0005 (Munni Bai, expired life cert)** — suspended cleanly, not disbursed.
6. **PPO-UP-VR-0006 (Hari Prasad, already paid)** — skipped without action. No double-payment.

## The scoreboard

| Axis | Result |
| --- | --- |
| `goal_reached` | PASS — all 7 cases handled correctly |
| `rules_upheld` | PASS — 0 of 5 failure conditions triggered |
| `cost_used` | $0.1544 — 26 tool calls, 37k tokens (threshold $0.50) |

## The pitch (15 seconds)

> "Today: one world, one agent, one scenario. The architecture is built so the second world drops in without restructuring anything. v2 is a library — UP property registration, GST filing, FASTag disputes, pension across other states. Every world built from real CAG-grade research. That's the moat: bureaucratic fidelity, not framework."

## What to NOT say

- Don't oversell as a "platform" — it's an MVP testbed with one world. The vision is platform; the demo is solution+validation.
- Don't claim framework-agnostic — the MVP is LangGraph-only. MCP is the deployment protocol, not yet the runtime intake.
- Don't claim multi-agent — the MVP is a single ReAct agent. Multi-agent is a v2 extension at the same architectural seam (`build_graph`).

## Honest answers if asked

**Q: Why pre-2025 control regime?**
> Because the post-Chitrakoot SOP fixed several of these gaps in real life. Simulating the strengthened regime would eliminate the adversarial scenarios that make the testbed meaningful. Post-SOP is a second world variant for v2.

**Q: How long did the world take to model?**
> Research: 25 minutes (CAG/RTI study). World code: under an hour. Most of that time was the schemas — once those are right, tools and rules write themselves.

**Q: What about HITL and CI/CD?**
> Deferred. HITL gating is a v2 feature for production rollouts. CI/CD integration is implicit — compositions, scenarios, and scorers are all versioned files.

**Q: Why LangGraph over CrewAI?**
> State machine semantics fit bureaucracy directly. Also, LangGraph's compiled graph is a single object we can swap in `build_graph(tools)` — perfect for the testbed's "agent under test" contract.
