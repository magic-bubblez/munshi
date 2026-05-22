"""Trace — the canonical event log shape read by scorers and replay UI.

Lives in Inspect AI's TaskState.store under TRACE_STORE_KEY. Both the world
(via the MCP server) and the solver (for agent messages) write through a
shared TraceWriter.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

TRACE_STORE_KEY = "munshi.trace"


class EventKind(StrEnum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    RULE_VIOLATION = "rule_violation"
    STATE_DELTA = "state_delta"
    AGENT_MESSAGE = "agent_message"


class TraceEvent(BaseModel):
    timestamp: datetime
    actor: str
    kind: EventKind
    payload: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    events: list[TraceEvent] = Field(default_factory=list)
    final_state_snapshot: dict[str, Any] | None = None

    def of_kind(self, kind: EventKind) -> list[TraceEvent]:
        return [e for e in self.events if e.kind == kind]

    def by_actor(self, actor: str) -> list[TraceEvent]:
        return [e for e in self.events if e.actor == actor]


class TraceWriter:
    """Append-only writer over a Trace instance.

    Designed to be cheap to call from inside tool implementations and from
    the solver's LangGraph callbacks.
    """

    def __init__(self, trace: Trace) -> None:
        self._trace = trace

    @property
    def trace(self) -> Trace:
        return self._trace

    def emit(
        self,
        actor: str,
        kind: EventKind,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._trace.events.append(
            TraceEvent(
                timestamp=datetime.now(timezone.utc),
                actor=actor,
                kind=kind,
                payload=payload or {},
            )
        )

    def snapshot_final_state(self, state: dict[str, Any]) -> None:
        self._trace.final_state_snapshot = state
