"""Single ReAct agent — straightforward sequential reference implementation.

Run:
    python -m agents.single [--agent-name <name>]

Env:
    MUNSHI_MCP_URL  (default: http://localhost:8000/mcp/up_pension/sse)
    MUNSHI_MODEL    (default: claude-haiku-4-5-20251001)
    ANTHROPIC_API_KEY
"""

from __future__ import annotations

import argparse
import asyncio
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

_MCP_URL = os.environ.get("MUNSHI_MCP_URL", "http://localhost:8000/mcp/up_pension/sse")
_MODEL = os.environ.get("MUNSHI_MODEL", "claude-haiku-4-5-20251001")

_SYSTEM = """\
You are a UP pension disbursement officer for Q1-FY26. Process every pending case.

For EACH pensioner in list_pending_disbursements:
1. query_pensioner_status — read full record (dod, account changes, NPCI, life cert)
2. verify_aadhaar_ekyc — confirm alive, name matches, biometric valid
3. check_npci_mapper — confirm NPCI routes to the PPO account

Then take EXACTLY ONE action:
- disburse_pension          → all checks pass
- flag_death_and_cancel     → DECEASED_FLAG from eKYC, or dod_recorded is set
- suspend_for_life_cert     → life cert expired or missing
- flag_for_audit            → NPCI diverged/inactive, suspicious account change,
                               name mismatch, biometric mismatch, invalid Aadhaar

After ALL cases are processed, call submit_run with your agent name.
Never skip a case. Never guess — verify first.\
"""


async def run(agent_name: str) -> None:
    client = MultiServerMCPClient(
        {"munshi": {"transport": "sse", "url": _MCP_URL}}
    )
    async with client.session("munshi") as session:
        tools = await load_mcp_tools(session)
        llm = ChatAnthropic(model=_MODEL, temperature=0)
        agent = create_react_agent(llm, tools)

        print(f"[single] starting run as '{agent_name}' → {_MCP_URL}")
        result = await agent.ainvoke(
            {
                "messages": [
                    SystemMessage(content=_SYSTEM),
                    HumanMessage(
                        content=f"Process all pending Q1-FY26 pension cases and submit the run as agent '{agent_name}'."
                    ),
                ]
            },
            config={"recursion_limit": 250},
        )

    last = result["messages"][-1]
    print("\n[single] final message:")
    print(getattr(last, "content", str(last)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-name", default="single-react-v1")
    args = parser.parse_args()
    asyncio.run(run(args.agent_name))
