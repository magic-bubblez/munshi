"""FastMCP server for the UP pension world.

This is the deployment artifact — exposes the world's tools over the Model
Context Protocol so any MCP-aware agent can connect. The testbed itself runs
tools in-process (via `tools.make_tools`) for speed; this server is what you
ship when an external agent wants to call the world remotely.

Run with: `python -m worlds.up_pension.server`
"""

from __future__ import annotations

from fastmcp import FastMCP

from munshi.trace import Trace, TraceWriter
from worlds.up_pension.schemas import PensionWorldState
from worlds.up_pension.tools import make_tools


def build_server(state: PensionWorldState | None = None) -> FastMCP:
    """Build an MCP server bound to a fresh (or supplied) world state.

    The server owns one TraceWriter — events emitted by tool calls are
    accumulated and can be retrieved by an out-of-band introspection tool
    or written to disk. For the MVP this server is not used by the testbed.
    """
    state = state or PensionWorldState()
    writer = TraceWriter(Trace())
    server: FastMCP = FastMCP("up-pension")

    for tool in make_tools(state, writer):
        server.add_tool(tool)

    return server


if __name__ == "__main__":  # pragma: no cover
    server = build_server()
    server.run()
