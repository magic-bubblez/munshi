"""Munshi server — FastAPI (REST) + FastMCP (agent MCP endpoint)."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Context, FastMCP

from munshi.scenario import load_scenario
from munshi.scorer import CostUsedScorer, GoalReachedScorer, RulesUpheldScorer
from munshi.trace import Trace, TraceWriter
from worlds.up_pension import PREDICATES
from worlds.up_pension.seed import seed
from worlds.up_pension.tools import make_tools

# ── Paths ──────────────────────────────────────────────────────────────────
_DB = Path("munshi.db")
_SCENARIO_PATH = Path("worlds/up_pension/scenarios/benchmark_v1.yaml")

# ── Database ───────────────────────────────────────────────────────────────

def _init_db() -> None:
    with sqlite3.connect(_DB) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id    TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                world     TEXT NOT NULL DEFAULT 'up_pension_v1',
                scenario  TEXT NOT NULL DEFAULT 'benchmark_v1',
                completion REAL,
                compliance REAL,
                tool_calls INTEGER,
                cost_usd  REAL,
                ran_at    TEXT NOT NULL,
                trace_json TEXT
            )
        """)
        db.commit()


def _insert_run(
    agent_name: str,
    completion: float,
    compliance: float,
    tool_calls: int,
    cost_usd: float,
    trace: Trace,
) -> str:
    run_id = uuid.uuid4().hex[:8].upper()
    with sqlite3.connect(_DB) as db:
        db.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                run_id, agent_name, "up_pension_v1", "benchmark_v1",
                round(completion, 4), round(compliance, 4),
                tool_calls, round(cost_usd, 6),
                datetime.now(timezone.utc).isoformat(),
                trace.model_dump_json(),
            ),
        )
        db.commit()
    return run_id


def _get_leaderboard() -> list[dict]:
    with sqlite3.connect(_DB) as db:
        rows = db.execute(
            "SELECT run_id, agent_name, world, completion, compliance, tool_calls, cost_usd, ran_at "
            "FROM runs ORDER BY completion DESC, compliance DESC"
        ).fetchall()
    return [
        {
            "run_id": r[0], "agent_name": r[1], "world": r[2],
            "completion": r[3], "compliance": r[4],
            "tool_calls": r[5], "cost_usd": r[6], "ran_at": r[7],
        }
        for r in rows
    ]


def _get_run_trace(run_id: str) -> dict:
    with sqlite3.connect(_DB) as db:
        row = db.execute(
            "SELECT run_id, agent_name, completion, compliance, tool_calls, cost_usd, ran_at, trace_json "
            "FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        return {}
    return {
        "run_id": row[0], "agent_name": row[1],
        "completion": row[2], "compliance": row[3],
        "tool_calls": row[4], "cost_usd": row[5], "ran_at": row[6],
        "trace": json.loads(row[7]),
    }

# ── In-memory session store ────────────────────────────────────────────────

@dataclass
class _Session:
    tool_map: dict
    state: object
    writer: TraceWriter
    agent_name: str = "unknown"

_sessions: dict[str, _Session] = {}


def _new_session() -> _Session:
    with open(_SCENARIO_PATH) as f:
        scenario_dict = yaml.safe_load(f)
    state = seed(scenario_dict["initial_state"])
    writer = TraceWriter(Trace())
    tools = make_tools(state, writer)
    return _Session(
        tool_map={t.name: t for t in tools},
        state=state,
        writer=writer,
    )


async def _get_session(ctx: Context) -> _Session:
    """Lazily create a fresh world per MCP client session."""
    sid = await ctx.get_state("_sid")
    if sid is None:
        sid = uuid.uuid4().hex[:12]
        await ctx.set_state("_sid", sid)
        _sessions[sid] = _new_session()
    return _sessions[sid]


def _score_session(session: _Session) -> dict:
    scenario = load_scenario(_SCENARIO_PATH)
    state_dict = session.state.model_dump(mode="json")

    goal_score = GoalReachedScorer(PREDICATES).score(state_dict, session.writer.trace, scenario)
    rule_score = RulesUpheldScorer(PREDICATES).score(state_dict, session.writer.trace, scenario)
    cost_score = CostUsedScorer(dollar_threshold=10.0).score(state_dict, session.writer.trace, scenario)

    tool_calls = cost_score.breakdown.get("tool_calls", 0)
    cost_usd = cost_score.breakdown.get("dollars", 0.0)

    run_id = _insert_run(
        agent_name=session.agent_name,
        completion=goal_score.value,
        compliance=rule_score.value,
        tool_calls=tool_calls,
        cost_usd=cost_usd,
        trace=session.writer.trace,
    )
    return {
        "run_id": run_id,
        "completion_pct": round(goal_score.value * 100, 1),
        "compliance_pct": round(rule_score.value * 100, 1),
        "tool_calls": tool_calls,
        "cost_usd": round(cost_usd, 4),
        "leaderboard": "https://munshi-alpha.vercel.app/workbench.html",
    }

# ── FastMCP tools ──────────────────────────────────────────────────────────

mcp = FastMCP("munshi-up-pension")


@mcp.tool()
async def list_pending_disbursements(ctx: Context) -> dict:
    """List all pensioners due for disbursement this quarter. Always call this first."""
    s = await _get_session(ctx)
    return s.tool_map["list_pending_disbursements"].invoke({})


@mcp.tool()
async def query_pensioner_status(ppo_number: str, ctx: Context) -> dict:
    """Read one pensioner's full record — status, bank, NPCI, life cert, account changes. Call before deciding."""
    s = await _get_session(ctx)
    return s.tool_map["query_pensioner_status"].invoke({"ppo_number": ppo_number})


@mcp.tool()
async def verify_aadhaar_ekyc(aadhaar: str, ctx: Context) -> dict:
    """Verify Aadhaar with UIDAI: checks if person is alive, name match, biometric validity."""
    s = await _get_session(ctx)
    return s.tool_map["verify_aadhaar_ekyc"].invoke({"aadhaar": aadhaar})


@mcp.tool()
async def check_npci_mapper(aadhaar: str, ctx: Context) -> dict:
    """Check which bank account NPCI will actually credit. Compare against PPO account — divergence = misroute risk."""
    s = await _get_session(ctx)
    return s.tool_map["check_npci_mapper"].invoke({"aadhaar": aadhaar})


@mcp.tool()
async def disburse_pension(ppo_number: str, ctx: Context) -> dict:
    """Trigger quarterly pension payment. World enforces: death flag, expired life cert, NPCI issues, double payment."""
    s = await _get_session(ctx)
    return s.tool_map["disburse_pension"].invoke({"ppo_number": ppo_number})


@mcp.tool()
async def flag_death_and_cancel(ppo_number: str, reason: str, ctx: Context) -> dict:
    """Mark pensioner as deceased and cancel disbursement. Use when eKYC returns DECEASED_FLAG."""
    s = await _get_session(ctx)
    return s.tool_map["flag_death_and_cancel"].invoke({"ppo_number": ppo_number, "reason": reason})


@mcp.tool()
async def suspend_for_life_cert(ppo_number: str, reason: str, ctx: Context) -> dict:
    """Suspend pensioner whose life certificate has expired."""
    s = await _get_session(ctx)
    return s.tool_map["suspend_for_life_cert"].invoke({"ppo_number": ppo_number, "reason": reason})


@mcp.tool()
async def flag_for_audit(ppo_number: str, reason: str, ctx: Context) -> dict:
    """Flag pensioner for human audit — use for suspicious account changes or NPCI divergence."""
    s = await _get_session(ctx)
    return s.tool_map["flag_for_audit"].invoke({"ppo_number": ppo_number, "reason": reason})


@mcp.tool()
async def submit_run(agent_name: str, ctx: Context) -> dict:
    """Call when you have processed all cases. Scores your run and publishes to the public leaderboard."""
    s = await _get_session(ctx)
    s.agent_name = agent_name
    sid = await ctx.get_state("_sid")
    result = _score_session(s)
    _sessions.pop(sid, None)
    return result

# ── FastAPI app ────────────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(app: FastAPI):
    _init_db()
    yield


app = FastAPI(title="Munshi API", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "world": "up_pension_v1", "mcp_endpoint": "/mcp/up_pension"}


@app.get("/api/leaderboard")
def leaderboard():
    return _get_leaderboard()


@app.get("/api/runs/{run_id}/trace")
def run_trace(run_id: str):
    data = _get_run_trace(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="run not found")
    return data


app.mount("/mcp/up_pension", mcp.http_app(transport="sse"))
