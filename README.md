# Munshi

A testbed for AI agent teams working on Indian bureaucratic workflows. You bring an agent team; Munshi gives you a simulated world to test it in, plus a scoreboard and a replay trace.

## How it works

1. Pick a world (UP pension disbursement, property registration, GST filing, passport renewal etc. 100s of templates).
2. Bring an agent team. Any framework that can speak the MCP works.
3. Define a scenario — initial state + success criteria + failure conditions.
4. Munshi runs the agent against the world, scores the run on **completion**, **rule compliance**, and **cost**, and emits a replay trace.

## Architecture

The codebase has two layers, and only two:

- **`munshi/`** — platform package. World-agnostic primitives only: the base `Scenario` model, the `Scorer` interface, the LangGraph → Inspect AI solver wrapper, the Task factory.
- **`worlds/<name>/`** — a fully self-contained world bundle. Owns its own research, schemas, tools, rules, scorers, scenarios, and reference agents. Portable. Removable. Addable without touching anything else.

The platform never imports from a world; worlds import from the platform. The dependency direction is the scalability guarantee.

## An example World (currently implemented)

### `worlds/up_pension/`

Uttar Pradesh social pension disbursement — Vridha, Vidhwa, and Divyang schemes.

Models the famous failure modes flagged in CAG audits and RTI investigations:

- Ghost pensioners (deceased beneficiaries still receiving disbursements)
- Expired or unverified KYC
- Duplicate Aadhaar linking across accounts
- DBT bounces from stale IFSC or Aadhaar-seed mismatch
- Wrong scheme assignment
- Double disbursement within a cycle

The world exposes its tools over an MCP server. The reference agent in `worlds/up_pension/agents/default/` is a LangGraph multi-agent team built specifically to handle these cases correctly.

## Tech stack

| Layer | Choice |
| --- | --- |
| World / tool surface | FastMCP (MCP server) |
| Schemas and state | Pydantic v2 |
| Agent framework (reference agent) | LangGraph |
| Model | Claude Sonnet 4.6 via Anthropic API |
| Eval harness | Inspect AI |
| Replay UI | Inspect View (built-in) |

## Running

```bash
# install
uv pip install -e .

# set up the model
cp .env.example .env  # add ANTHROPIC_API_KEY

# run the testbed against the UP pension world
inspect eval worlds/up_pension/task.py

# open the replay UI
inspect view
```

## Status

MVP build. One world (UP pension), one reference agent team, one scenario triggering multiple famous failure modes, three default scorers. The architecture is built for the subsequent worlds to be added without restructuring.

## Roadmap

Each world is a research project as much as a software project. Future worlds in scope:

- UP property registration
- GST filing (small business path)
- Passport renewal
- FASTag dispute resolution
- Scholarship disbursement
- Ration card update
- FIR filing
