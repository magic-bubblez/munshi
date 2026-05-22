"""Default reference agent for the UP pension world.

A single ReAct agent powered by Claude Sonnet 4.6, with the full pension tool
surface. The system prompt enforces the investigate-then-act discipline.

This is intentionally the simplest reliable shape. The graph_builder seam is
the place to swap in a multi-agent composition (supervisor + specialists)
without changing the world, scenario, or scorers.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from worlds.up_pension.agents.default.prompts import SYSTEM_PROMPT

MODEL_ID = "claude-sonnet-4-6"


def build_graph(tools: list[BaseTool]) -> CompiledStateGraph:
    """Construct the agent graph bound to the given world tools.

    Called fresh per scenario run by the Munshi solver — tools close over
    that run's world state and trace writer.
    """
    llm = ChatAnthropic(
        model_name=MODEL_ID,
        temperature=0,
        max_tokens_to_sample=2048,
        timeout=60.0,
        stop=None,
    )
    return create_react_agent(
        llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
