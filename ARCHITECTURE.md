# Munshi — Architecture Contracts

This document defines the **seams** of Munshi: the type signatures, interfaces, and dependency rules that every world and every agent must respect. It contains no implementation logic. Everything below is the contract surface.

## Dependency rule (the one invariant that makes everything else work)

```
  worlds/<name>/   ──imports──►   munshi/
       │
       └── never imports another world
```

- The platform package (`munshi/`) **never** imports from any world.
- Every world imports from `munshi/` to fulfill its contracts.
- Worlds **never** import from each other.

Violating this rule breaks portability. Enforce it in code review.

---

## The four primary contracts

### 1. `Scenario` — platform-level base model

A scenario is a declarative test case. World-agnostic in shape; world-specific in content.

```python
# munshi/scenario.py

class Scenario(BaseModel):
    name: str
    description: str
    world: str                          # e.g. "up_pension"
    initial_state: dict[str, Any]       # opaque to platform; the world deserializes
    goal: GoalSpec                      # see below
    failure_conditions: list[str]       # names of world-registered predicates

class GoalSpec(BaseModel):
    predicate_name: str                 # name registered by the world
    expected: Any | None = None         # optional comparison value
```

Worlds extend this by parsing `initial_state` into their own typed seed format and registering their predicates. The platform never inspects `initial_state` directly.

---

### 2. `World` contract — per-world, fulfilled by convention not inheritance

Every world directory must expose these symbols (no abstract base class — Python conventions enforce it):

```python
# worlds/<name>/__init__.py must re-export:

WORLD_NAME: str                         # canonical id, must match scenario.world
SCHEMAS: type[BaseModel]                # root state schema (e.g. PensionWorldState)
SEED: Callable[[dict], BaseModel]       # builds state from scenario.initial_state
PREDICATES: dict[str, Predicate]        # name → predicate fn (used by goal/failure)
SERVER_FACTORY: Callable[[BaseModel], MCPServer]
                                        # builds an MCP server bound to a state instance

class Predicate(Protocol):
    def __call__(self, state: BaseModel, trace: Trace) -> PredicateResult: ...

class PredicateResult(BaseModel):
    passed: bool
    reason: str
    details: dict[str, Any] = {}
```

Why no ABC: forcing inheritance from a platform class would couple worlds tighter than needed. A duck-typed module surface is enough and keeps each world a standalone bundle.

---

### 3. `Score` and `Scorer` — platform-level

```python
# munshi/scorer.py

class Score(BaseModel):
    axis: Literal["completion", "compliance", "cost"]
    value: float                        # always normalized to [0.0, 1.0] for completion/compliance
                                        # cost in absolute units (dollars), with notes
    passed: bool                        # convenience boolean per axis
    breakdown: dict[str, Any]           # axis-specific detail
    explanation: str

class Scorer(Protocol):
    name: str
    axis: Literal["completion", "compliance", "cost"]
    def score(
        self,
        final_state: BaseModel,
        trace: Trace,
        scenario: Scenario,
    ) -> Score: ...
```

The platform ships **three default scorer factories** that any world can use by binding world-specific predicates:

- `goal_reached_scorer(predicates)` — runs scenario.goal predicate
- `rules_uphold_scorer(predicates)` — runs all scenario.failure_conditions
- `cost_used_scorer()` — sums tokens/tool-calls from trace; world-agnostic

Worlds may add custom scorers in their own `scorers.py` (e.g. `correct_amount_disbursed`).

---

### 4. `Trace` — the canonical event log

Trace lives in Inspect AI's `TaskState.store` under a known key. It is a structured event log that scorers and the replay UI read from.

```python
# munshi/trace.py

class TraceEvent(BaseModel):
    timestamp: datetime
    actor: str                          # agent node name or "world"
    kind: Literal[
        "tool_call",                    # agent called a world tool
        "tool_result",                  # world returned a result
        "rule_violation",               # world raised on an invariant
        "state_delta",                  # world state changed
        "agent_message",                # LLM message
    ]
    payload: dict[str, Any]

class Trace(BaseModel):
    events: list[TraceEvent]
    final_state_snapshot: dict[str, Any] | None
```

The world is responsible for emitting `tool_call`, `tool_result`, `rule_violation`, and `state_delta`. The Solver is responsible for emitting `agent_message`. Both write through a shared `TraceWriter` injected via Inspect's store.

---

## The platform package surface

```python
# munshi/__init__.py — the only public symbols
__all__ = [
    "Scenario", "GoalSpec",
    "Score", "Scorer",
    "TraceEvent", "Trace", "TraceWriter",
    "Predicate", "PredicateResult",
    "build_solver",                     # LangGraph → Inspect Solver wrapper
    "build_task",                       # the @task factory
    "goal_reached_scorer",              # default scorers
    "rules_uphold_scorer",
    "cost_used_scorer",
]
```

Anything not in this list is platform-internal and worlds must not import it.

---

## The Solver wrapper — how an agent becomes runnable

```python
# munshi/solver.py

def build_solver(
    graph: CompiledStateGraph,          # a LangGraph compiled graph
    mcp_server_factory: Callable[[BaseModel], MCPServer],
    seed_fn: Callable[[dict], BaseModel],
) -> Solver:
    """
    Returns an Inspect Solver that:
      1. Builds a fresh world state from sample.input (the scenario)
      2. Starts the world's MCP server bound to that state
      3. Connects the LangGraph agent to the MCP server
      4. Runs the agent with a hard step cap
      5. Emits agent_message events to the trace
      6. On termination, snapshots final state into the trace
    """
```

This is the only place LangGraph and Inspect AI meet. Everything else stays independent of both.

---

## The Task factory — the entry point

```python
# munshi/task_factory.py

def build_task(
    *,
    world_module: ModuleType,           # e.g. worlds.up_pension
    scenarios_dir: Path,                # directory of scenario YAMLs
    agent_graph: CompiledStateGraph,
    extra_scorers: list[Scorer] = [],
) -> Task:
    """
    Wires everything into an Inspect @task:
      - Dataset = scenarios in scenarios_dir, deserialized as Scenario
      - Solver = build_solver(agent_graph, world_module.SERVER_FACTORY, world_module.SEED)
      - Scorers = three defaults bound to world_module.PREDICATES, plus extras
    """
```

Each world's `task.py` is a 5-line file that imports this factory, passes its locals in, and exposes the result. That's the entrypoint Inspect runs.

---

## Decisions locked

| Question | Decision |
| --- | --- |
| Goal/failure as predicates or LLM-judged? | **Predicates.** World registers them by name. LLM-judge reserved for explicit "fuzzy" custom scorers. |
| Termination policy | **Hard step cap (default 30) + goal predicate short-circuit.** |
| Agent state visibility | **Tools-only.** Agent never sees world state except through tool returns. |
| Scenario goal/failure shape | **Trace-aware predicates** — receive both final state and full trace. Lets us write predicates like "must have called `verify_aadhaar` before `disburse_pension`". |
| World defines its own MCP namespace? | **Yes.** All tools live under the world's MCP server. No name collisions possible. |
| Composition (agent graph) versioned as data? | **Deferred.** MVP hard-codes one graph in `worlds/up_pension/agents/default/graph.py`. v2 makes compositions declarative. |
| One MCP server per scenario run? | **Yes.** Fresh state per run. Server spun up, used, torn down. Deterministic. |

---

## What this contract gets you

1. **A second world** is a copy of `worlds/up_pension/`, fill in the schemas/tools/predicates. Zero platform changes.
2. **A second agent** for an existing world drops into `worlds/<name>/agents/<variant>/`. Zero changes elsewhere.
3. **A second scorer** is a new file in the world's `scorers.py`. Pass it through `extra_scorers` in the world's `task.py`.
4. **A new scenario** is a YAML in the world's `scenarios/`. No code changes at all.

This is the design floor for everything that comes next.
