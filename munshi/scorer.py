"""Scorer contract + three default scorer factories.

Scoring is split into three INDEPENDENT axes: completion, compliance, cost.
Never conflate them into one number — that's the testbed's entire point.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from munshi.scenario import Predicate, Scenario
from munshi.trace import EventKind, Trace


class Axis(StrEnum):
    COMPLETION = "completion"
    COMPLIANCE = "compliance"
    COST = "cost"


class Score(BaseModel):
    axis: Axis
    value: float
    passed: bool
    breakdown: dict[str, Any] = Field(default_factory=dict)
    explanation: str


class Scorer(Protocol):
    name: str
    axis: Axis

    def score(
        self,
        final_state: Any,
        trace: Trace,
        scenario: Scenario,
    ) -> Score: ...


# ---------------------------------------------------------------------------
# Default scorer factories
# ---------------------------------------------------------------------------


class GoalReachedScorer:
    """Runs scenario.goal predicate against final state + trace.

    Completion is binary: the predicate passed or it didn't.
    """

    name = "goal_reached"
    axis = Axis.COMPLETION

    def __init__(self, predicates: dict[str, Predicate]) -> None:
        self._predicates = predicates

    def score(
        self,
        final_state: Any,
        trace: Trace,
        scenario: Scenario,
    ) -> Score:
        predicate_name = scenario.goal.predicate_name
        if predicate_name not in self._predicates:
            return Score(
                axis=self.axis,
                value=0.0,
                passed=False,
                explanation=f"goal predicate '{predicate_name}' not registered by world",
            )
        result = self._predicates[predicate_name](final_state, trace)
        return Score(
            axis=self.axis,
            value=1.0 if result.passed else 0.0,
            passed=result.passed,
            breakdown=result.details,
            explanation=result.reason,
        )


class RulesUpheldScorer:
    """Runs every failure-condition predicate. Counts violations.

    Compliance value = 1 - (violations / total_checked). 1.0 = no rule broken.
    """

    name = "rules_upheld"
    axis = Axis.COMPLIANCE

    def __init__(self, predicates: dict[str, Predicate]) -> None:
        self._predicates = predicates

    def score(
        self,
        final_state: Any,
        trace: Trace,
        scenario: Scenario,
    ) -> Score:
        checked = scenario.failure_conditions
        if not checked:
            return Score(
                axis=self.axis,
                value=1.0,
                passed=True,
                explanation="no failure conditions declared",
            )

        results: dict[str, dict[str, Any]] = {}
        violations = 0
        for name in checked:
            if name not in self._predicates:
                results[name] = {"status": "missing", "reason": "predicate not registered"}
                violations += 1
                continue
            result = self._predicates[name](final_state, trace)
            results[name] = {
                "passed": result.passed,
                "reason": result.reason,
                "details": result.details,
            }
            if not result.passed:
                violations += 1

        value = 1.0 - (violations / len(checked))
        return Score(
            axis=self.axis,
            value=value,
            passed=violations == 0,
            breakdown={"results": results, "violations": violations, "checked": len(checked)},
            explanation=f"{violations}/{len(checked)} failure conditions triggered",
        )


class CostUsedScorer:
    """Counts tool calls and (when available) tokens from the trace.

    Cost is world-agnostic. Value is the dollar estimate (or proxy).
    `passed=True` if under threshold, else False. Default threshold = $1.00.
    """

    name = "cost_used"
    axis = Axis.COST

    def __init__(self, dollar_threshold: float = 1.0) -> None:
        self._threshold = dollar_threshold

    def score(
        self,
        final_state: Any,
        trace: Trace,
        scenario: Scenario,
    ) -> Score:
        tool_calls = len(trace.of_kind(EventKind.TOOL_CALL))
        agent_messages = trace.of_kind(EventKind.AGENT_MESSAGE)

        input_tokens = sum(e.payload.get("input_tokens", 0) for e in agent_messages)
        output_tokens = sum(e.payload.get("output_tokens", 0) for e in agent_messages)
        dollars = sum(e.payload.get("dollars", 0.0) for e in agent_messages)

        return Score(
            axis=self.axis,
            value=dollars,
            passed=dollars <= self._threshold,
            breakdown={
                "tool_calls": tool_calls,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "dollars": dollars,
                "threshold": self._threshold,
            },
            explanation=(
                f"{tool_calls} tool calls, {input_tokens + output_tokens} tokens, "
                f"${dollars:.4f} (threshold ${self._threshold:.2f})"
            ),
        )


def goal_reached_scorer(predicates: dict[str, Predicate]) -> Scorer:
    return GoalReachedScorer(predicates)


def rules_upheld_scorer(predicates: dict[str, Predicate]) -> Scorer:
    return RulesUpheldScorer(predicates)


def cost_used_scorer(dollar_threshold: float = 1.0) -> Scorer:
    return CostUsedScorer(dollar_threshold)
