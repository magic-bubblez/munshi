"""Task factory — assembles an Inspect AI Task from world + scenarios + agent.

Each world's `task.py` is a 5-line file that imports `build_task` and passes
in its module-level exports.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import Score as InspectScore
from inspect_ai.scorer import Scorer as InspectScorer
from inspect_ai.scorer import Target, scorer as inspect_scorer
from inspect_ai.solver import TaskState
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from munshi.scenario import Scenario, load_scenarios_dir
from munshi.scorer import (
    Axis,
    Scorer,
    cost_used_scorer,
    goal_reached_scorer,
    rules_upheld_scorer,
)
from munshi.solver import SCENARIO_METADATA_KEY, build_solver
from munshi.trace import TRACE_STORE_KEY, Trace


def build_task_components(
    *,
    world_module: ModuleType,
    scenarios_dir: Path | str,
    graph_builder: Callable[[list[BaseTool]], CompiledStateGraph],
    extra_scorers: list[Scorer] | None = None,
    step_cap: int = 30,
    cost_threshold_dollars: float = 1.0,
) -> dict[str, Any]:
    """Assemble the components needed to construct an Inspect Task.

    Returns a dict with `dataset`, `solver`, `scorer` ready to pass to
    `Task(**components)`. The world's task.py applies the `@task` decorator
    directly so Inspect's CLI can discover it during module introspection.
    """

    predicates = _require(world_module, "PREDICATES")
    seed_fn = _require(world_module, "SEED")
    tools_fn = _require(world_module, "TOOLS_FACTORY")
    state_dumper = _require(world_module, "STATE_DUMPER")
    world_name = _require(world_module, "WORLD_NAME")

    scenarios = load_scenarios_dir(scenarios_dir)
    _assert_scenarios_target_world(scenarios, world_name)

    dataset = MemoryDataset(
        [
            Sample(
                input=s.description,
                id=s.name,
                metadata={SCENARIO_METADATA_KEY: s.model_dump()},
            )
            for s in scenarios
        ]
    )

    munshi_scorers: list[Scorer] = [
        goal_reached_scorer(predicates),
        rules_upheld_scorer(predicates),
        cost_used_scorer(cost_threshold_dollars),
    ]
    munshi_scorers.extend(extra_scorers or [])

    inspect_scorers = [_adapt_scorer(s) for s in munshi_scorers]

    return {
        "dataset": dataset,
        "solver": build_solver(
            seed_fn=seed_fn,
            tools_fn=tools_fn,
            graph_builder=graph_builder,
            state_dumper=state_dumper,
            step_cap=step_cap,
        ),
        "scorer": inspect_scorers,
    }


# Backwards-compatible alias retained intentionally — `build_task` was the
# original public name in ARCHITECTURE.md. Callers that re-export it from
# `munshi.__init__` get a function that returns the components dict.
build_task = build_task_components


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _require(module: ModuleType, name: str) -> Any:
    if not hasattr(module, name):
        raise AttributeError(
            f"world module {module.__name__!r} is missing required export {name!r}"
        )
    return getattr(module, name)


def _assert_scenarios_target_world(scenarios: list[Scenario], world_name: str) -> None:
    for s in scenarios:
        if s.world != world_name:
            raise ValueError(
                f"scenario {s.name!r} targets world {s.world!r}, "
                f"but task is built for world {world_name!r}"
            )


def _adapt_scorer(munshi_scorer: Scorer) -> InspectScorer:
    """Wrap a Munshi Scorer as an Inspect AI scorer registered by axis name."""

    @inspect_scorer(metrics=[], name=munshi_scorer.name)
    def adapted() -> InspectScorer:
        async def _score(state: TaskState, target: Target) -> InspectScore:
            trace: Trace = state.store.get(TRACE_STORE_KEY) or Trace()
            scenario = Scenario.model_validate(
                state.metadata[SCENARIO_METADATA_KEY]
            )
            final_state = trace.final_state_snapshot or {}
            result = munshi_scorer.score(final_state, trace, scenario)
            return InspectScore(
                value=_inspect_score_value(result.axis, result.value, result.passed),
                answer=result.explanation,
                explanation=result.explanation,
                metadata={
                    "axis": result.axis.value,
                    "passed": result.passed,
                    "breakdown": result.breakdown,
                    "scorer_name": munshi_scorer.name,
                },
            )

        return _score

    return adapted()


def _inspect_score_value(axis: Axis, value: float, passed: bool) -> Any:
    """Inspect renders Score.value in the log viewer. Use the most informative shape per axis."""
    if axis is Axis.COST:
        return value  # dollars, displayed numerically
    return "C" if passed else "I"  # Correct/Incorrect for the binary axes
