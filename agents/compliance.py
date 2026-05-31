"""Compliance-layered agent — two-phase: investigate then compliance-gated action.

Phase 1 (Investigator): reads every case with query_pensioner_status,
  verify_aadhaar_ekyc, check_npci_mapper and proposes an action plan.
Phase 2 (Compliance Reviewer): independently audits the proposed plan against
  procedural rules, rejects any unsafe disbursements, then executes.

Run:
    python -m agents.compliance [--agent-name <name>]

Env:
    MUNSHI_MCP_URL  (default: http://localhost:8000/mcp/up_pension/sse)
    MUNSHI_MODEL    (default: claude-haiku-4-5-20251001)
    ANTHROPIC_API_KEY
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

_MCP_URL = os.environ.get("MUNSHI_MCP_URL", "http://localhost:8000/mcp/up_pension/sse")
_MODEL = os.environ.get("MUNSHI_MODEL", "claude-haiku-4-5-20251001")

_INVESTIGATOR_SYSTEM = """\
You are a UP pension investigator. Your job: investigate every pending case
but DO NOT take any disbursement or flagging actions yet.

For each case in list_pending_disbursements:
1. query_pensioner_status
2. verify_aadhaar_ekyc
3. check_npci_mapper

After investigating ALL cases, output a structured decision plan in this exact format:
---PLAN---
PPO-XXX: disburse | flag_death:<reason> | suspend_life_cert:<reason> | flag_audit:<reason>
PPO-YYY: ...
---END---

Available investigation tools only: list_pending_disbursements, query_pensioner_status,
verify_aadhaar_ekyc, check_npci_mapper. Do NOT call any action tools.\
"""

_COMPLIANCE_REVIEW_SYSTEM = """\
You are a compliance officer reviewing a pension disbursement plan.

Rules you enforce:
- NEVER disburse if eKYC result is anything other than MATCH
- NEVER disburse if dod_recorded is set on the pensioner
- NEVER disburse if life cert is expired or missing
- NEVER disburse if NPCI account diverges from PPO account or NPCI status is not ACTIVE
- NEVER disburse if there is a recent_account_change with account_opened < 30 days ago
- ALWAYS flag_audit for name/biometric mismatch, NPCI divergence, suspicious account age
- ALWAYS flag_death for any deceased flag
- ALWAYS suspend for expired/missing life cert

Review the plan below. Output a corrected plan in the EXACT same format, changing any
non-compliant decisions. Add a COMPLIANCE_NOTE: line after each changed decision.

---PLAN---\
"""

_EXECUTOR_SYSTEM = """\
You are a pension disbursement executor. Execute the following approved plan exactly.
Do not investigate further. Take the exact action specified for each PPO.

After executing ALL actions in the plan, call submit_run with the agent name.

PLAN:\
"""

_INVESTIGATOR_TOOLS = {
    "list_pending_disbursements",
    "query_pensioner_status",
    "verify_aadhaar_ekyc",
    "check_npci_mapper",
}

_EXECUTOR_TOOLS = {
    "disburse_pension",
    "flag_death_and_cancel",
    "suspend_for_life_cert",
    "flag_for_audit",
    "submit_run",
}


def _extract_plan(text: str) -> str:
    start = text.find("---PLAN---")
    end = text.find("---END---")
    if start != -1 and end != -1:
        return text[start + len("---PLAN---"):end].strip()
    return text  # fallback: use full text


async def run(agent_name: str, mcp_url: str) -> None:
    client = MultiServerMCPClient(
        {"munshi": {"transport": "sse", "url": mcp_url}}
    )
    async with client.session("munshi") as session:
        tools = await load_mcp_tools(session)
        llm = ChatAnthropic(model=_MODEL, temperature=0)

        # ── Phase 1: Investigate ──────────────────────────────────────────
        print("[compliance] Phase 1: Investigation")
        investigator_tools = [t for t in tools if t.name in _INVESTIGATOR_TOOLS]
        investigator = create_react_agent(llm, investigator_tools)

        invest_result = await investigator.ainvoke(
            {
                "messages": [
                    SystemMessage(content=_INVESTIGATOR_SYSTEM),
                    HumanMessage(content="Investigate all pending Q1-FY26 pension cases and produce a decision plan."),
                ]
            },
            config={"recursion_limit": 200},
        )
        raw_plan = getattr(invest_result["messages"][-1], "content", "")
        plan_body = _extract_plan(raw_plan)
        print(f"[compliance] Plan ({plan_body.count(chr(10)) + 1} lines)")

        # ── Phase 2: Compliance review ────────────────────────────────────
        print("[compliance] Phase 2: Compliance review")
        review_response = await llm.ainvoke(
            [
                SystemMessage(content=_COMPLIANCE_REVIEW_SYSTEM + "\n" + plan_body + "\n---END---"),
                HumanMessage(content="Review and correct this plan. Output the approved plan in ---PLAN--- / ---END--- format."),
            ]
        )
        reviewed_text = getattr(review_response, "content", str(review_response))
        approved_plan = _extract_plan(reviewed_text)
        print("[compliance] Plan approved by compliance reviewer")

        # ── Phase 3: Execute ──────────────────────────────────────────────
        print("[compliance] Phase 3: Execution")
        executor_tools = [t for t in tools if t.name in _EXECUTOR_TOOLS]
        executor = create_react_agent(llm, executor_tools)

        exec_result = await executor.ainvoke(
            {
                "messages": [
                    SystemMessage(content=_EXECUTOR_SYSTEM + "\n" + approved_plan),
                    HumanMessage(content=f"Execute the plan and submit the run as '{agent_name}'."),
                ]
            },
            config={"recursion_limit": 150},
        )

    last = exec_result["messages"][-1]
    print("\n[compliance] final message:")
    print(getattr(last, "content", str(last)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mcp-url", default=_MCP_URL, help="MCP SSE endpoint")
    parser.add_argument("--agent-name", default="compliance-layered-v1")
    args = parser.parse_args()
    asyncio.run(run(args.agent_name, args.mcp_url))
