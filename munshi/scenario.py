"""Scenario contract — the declarative test case shape, world-agnostic."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import BaseModel, Field


class PredicateResult(BaseModel):
    """The verdict of one predicate evaluation."""

    passed: bool
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)


class Predicate(Protocol):
    """A world-registered predicate over final state and trace.

    Worlds register implementations in their PREDICATES dict; scenarios
    reference them by name. Trace-aware so predicates can express things
    like "must have called verify_aadhaar before disburse_pension".
    """

    def __call__(self, state: Any, trace: Any) -> PredicateResult: ...


class GoalSpec(BaseModel):
    """A scenario's success criterion. References a world-registered predicate."""

    predicate_name: str
    expected: Any | None = None


class Scenario(BaseModel):
    """A declarative test case.

    World-agnostic in shape; world-specific in content. The platform never
    inspects `initial_state` — the world's SEED fn deserializes it.
    """

    name: str
    description: str
    world: str
    initial_state: dict[str, Any]
    goal: GoalSpec
    failure_conditions: list[str] = Field(default_factory=list)


def load_scenario(path: Path | str) -> Scenario:
    """Read a YAML file into a Scenario model."""
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)
    return Scenario.model_validate(raw)


def load_scenarios_dir(directory: Path | str) -> list[Scenario]:
    """Read every *.yaml in a directory into Scenario models."""
    directory = Path(directory)
    return [load_scenario(p) for p in sorted(directory.glob("*.yaml"))]
