"""Munshi — testbed primitives for agentic systems on Indian bureaucratic workflows.

This is the platform package. It owns world-agnostic primitives only. Worlds
import from here; this package never imports from any world.
"""

from munshi.scenario import (
    GoalSpec,
    Predicate,
    PredicateResult,
    Scenario,
    load_scenario,
    load_scenarios_dir,
)
from munshi.scorer import (
    Axis,
    Score,
    Scorer,
    cost_used_scorer,
    goal_reached_scorer,
    rules_upheld_scorer,
)
from munshi.solver import SCENARIO_METADATA_KEY, build_solver
from munshi.task_factory import build_task
from munshi.trace import (
    TRACE_STORE_KEY,
    EventKind,
    Trace,
    TraceEvent,
    TraceWriter,
)

__all__ = [
    "Axis",
    "EventKind",
    "GoalSpec",
    "Predicate",
    "PredicateResult",
    "SCENARIO_METADATA_KEY",
    "Scenario",
    "Score",
    "Scorer",
    "TRACE_STORE_KEY",
    "Trace",
    "TraceEvent",
    "TraceWriter",
    "build_solver",
    "build_task",
    "cost_used_scorer",
    "goal_reached_scorer",
    "load_scenario",
    "load_scenarios_dir",
    "rules_upheld_scorer",
]
