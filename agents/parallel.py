"""Parallel multi-agent — one mini-agent per pensioner case, all concurrent.

Run:
    python -m agents.parallel [--agent-name <name>]

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
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

_MCP_URL = os.environ.get("MUNSHI_MCP_URL", "http://localhost:8000/mcp/up_pension/sse")
_MODEL = os.environ.get("MUNSHI_MODEL", "claude-haiku-4-5-20251001")

_CASE_SYSTEM = """\
You handle ONE pension case. Use the tools to investigate, then take exactly one action.

Steps:
1. query_pensioner_status({ppo_number})
2. verify_aadhaar_ekyc with the aadhaar from the status result
3. check_npci_mapper with the same aadhaar

Decision:
- disburse_pension          → all clear
- flag_death_and_cancel     → DECEASED_FLAG from eKYC, or dod_recorded is set
- suspend_for_life_cert     → life cert expired or missing
- flag_for_audit            → NPCI diverged/inactive, suspicious account change,
                               name mismatch, biometric mismatch, invalid Aadhaar

Take the action. Then stop — do not call submit_run.\
"""

_WORKER_TOOLS = {
    "query_pensioner_status",
    "verify_aadhaar_ekyc",
    "check_npci_mapper",
    "disburse_pension",
    "flag_death_and_cancel",
    "suspend_for_life_cert",
    "flag_for_audit",
}


def _parse_result(raw: object) -> dict:
    # MCP content-block list: [{"type": "text", "text": "..."}]
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "text" in raw[0]:
        raw = raw[0]["text"]
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
    return raw if isinstance(raw, dict) else {"raw": raw}


async def _handle_case(
    tools: list[BaseTool],
    llm: ChatAnthropic,
    semaphore: asyncio.Semaphore,
    ppo: str,
    idx: int,
    total: int,
) -> str:
    worker_tools = [t for t in tools if t.name in _WORKER_TOOLS]
    agent = create_react_agent(llm, worker_tools)

    async with semaphore:
        print(f"  [{idx}/{total}] processing {ppo}")
        result = await agent.ainvoke(
            {
                "messages": [
                    SystemMessage(content=_CASE_SYSTEM),
                    HumanMessage(content=f"Handle pension case {ppo}."),
                ]
            },
            config={"recursion_limit": 40},
        )

    last = result["messages"][-1]
    content = getattr(last, "content", str(last))
    print(f"  [{idx}/{total}] {ppo} done")
    return content


async def run(agent_name: str, mcp_url: str, concurrency: int = 5) -> None:
    client = MultiServerMCPClient(
        {"munshi": {"transport": "sse", "url": mcp_url}}
    )
    async with client.session("munshi") as session:
        tools = await load_mcp_tools(session)
        llm = ChatAnthropic(model=_MODEL, temperature=0)

        # List pending cases
        list_tool = next(t for t in tools if t.name == "list_pending_disbursements")
        raw = await list_tool.ainvoke({})
        parsed = _parse_result(raw)
        pending = parsed.get("result", parsed).get("pending", [])
        ppo_numbers = [c["ppo_number"] for c in pending]

        print(f"[parallel] {len(ppo_numbers)} cases → running {concurrency} at a time")

        semaphore = asyncio.Semaphore(concurrency)
        tasks = [
            _handle_case(tools, llm, semaphore, ppo, i + 1, len(ppo_numbers))
            for i, ppo in enumerate(ppo_numbers)
        ]
        await asyncio.gather(*tasks)

        # Submit run after all cases are processed
        submit_tool = next(t for t in tools if t.name == "submit_run")
        result = await submit_tool.ainvoke({"agent_name": agent_name})
        parsed = _parse_result(result)
        print("\n[parallel] run submitted:")
        print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mcp_url", nargs="?", default=_MCP_URL)
    parser.add_argument("agent_name", nargs="?", default="parallel-multi-agent-v1")
    args = parser.parse_args()
    asyncio.run(run(args.agent_name, args.mcp_url))
