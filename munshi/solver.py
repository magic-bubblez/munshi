"""Solver — bridges a LangGraph agent to Inspect AI.

The solver is the only place LangGraph and Inspect AI meet. Worlds and agents
stay independent of both.

Per-run lifecycle:
  1. Deserialize scenario from sample metadata
  2. Build a fresh world state via the world's seed_fn
  3. Build per-run tools (closed over state + trace writer)
  4. Build the agent graph (closed over tools)
  5. Invoke the graph with the scenario description as the user message
  6. Snapshot final world state into the trace
"""

from __future__ import annotations

from typing import Any, Callable

from inspect_ai.solver import Generate, Solver, TaskState, solver
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from munshi.scenario import Scenario
from munshi.trace import TRACE_STORE_KEY, EventKind, Trace, TraceWriter

SCENARIO_METADATA_KEY = "munshi.scenario"


def build_solver(
    *,
    seed_fn: Callable[[dict[str, Any]], Any],
    tools_fn: Callable[[Any, TraceWriter], list[BaseTool]],
    graph_builder: Callable[[list[BaseTool]], CompiledStateGraph],
    state_dumper: Callable[[Any], dict[str, Any]],
    step_cap: int = 30,
) -> Solver:
    """Construct an Inspect AI solver wrapping a LangGraph agent.

    Args:
        seed_fn: turns scenario.initial_state (dict) into the world's typed state.
        tools_fn: given world state and a trace writer, returns langchain tools
            whose implementations read/write state and emit trace events.
        graph_builder: given a list of tools, returns a compiled LangGraph.
        state_dumper: turns world state back into a serializable dict for the
            trace snapshot.
        step_cap: hard ceiling on LangGraph recursion. Prevents runaway loops.
    """

    @solver
    def munshi_solver() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            scenario = _read_scenario(state)

            trace = Trace()
            writer = TraceWriter(trace)
            state.store.set(TRACE_STORE_KEY, trace)

            world_state = seed_fn(scenario.initial_state)
            tools = tools_fn(world_state, writer)
            graph = graph_builder(tools)

            initial_messages = [HumanMessage(content=_build_user_prompt(scenario))]

            try:
                result = await graph.ainvoke(
                    {"messages": initial_messages},
                    config={"recursion_limit": step_cap},
                )
                _record_agent_messages(result, writer)
            except Exception as exc:
                writer.emit(
                    actor="solver",
                    kind=EventKind.AGENT_MESSAGE,
                    payload={"error": type(exc).__name__, "message": str(exc)},
                )

            writer.snapshot_final_state(state_dumper(world_state))
            return state

        return solve

    return munshi_solver()


def _read_scenario(state: TaskState) -> Scenario:
    raw = state.metadata.get(SCENARIO_METADATA_KEY)
    if raw is None:
        raise RuntimeError(
            f"sample metadata missing '{SCENARIO_METADATA_KEY}'; "
            "scenarios must be attached by the dataset loader"
        )
    return Scenario.model_validate(raw)


def _build_user_prompt(scenario: Scenario) -> str:
    return (
        f"# Scenario: {scenario.name}\n\n"
        f"{scenario.description}\n\n"
        "Use the tools available to you to handle this scenario. "
        "Adhere strictly to procedural rules — the world will reject "
        "tool calls that violate them."
    )


# Claude Sonnet 4.6 pricing (USD per token), used for the cost scorer.
_SONNET_INPUT_USD_PER_TOKEN = 3.0 / 1_000_000
_SONNET_OUTPUT_USD_PER_TOKEN = 15.0 / 1_000_000


def _record_agent_messages(graph_result: dict[str, Any], writer: TraceWriter) -> None:
    messages = graph_result.get("messages", [])
    for message in messages:
        if isinstance(message, AIMessage):
            usage = getattr(message, "usage_metadata", None) or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            dollars = (
                input_tokens * _SONNET_INPUT_USD_PER_TOKEN
                + output_tokens * _SONNET_OUTPUT_USD_PER_TOKEN
            )
            writer.emit(
                actor="agent",
                kind=EventKind.AGENT_MESSAGE,
                payload={
                    "content": _stringify_content(message.content),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "dollars": dollars,
                    "tool_calls": [
                        {"name": tc.get("name"), "args": tc.get("args")}
                        for tc in (getattr(message, "tool_calls", None) or [])
                    ],
                },
            )


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            else:
                parts.append(str(part))
        return "\n".join(parts)
    return str(content)
