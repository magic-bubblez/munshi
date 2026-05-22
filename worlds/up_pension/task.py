"""Inspect AI task entrypoint for the UP pension world.

Run with:  inspect eval worlds/up_pension/task.py
View with: inspect view
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from inspect_ai import Task, task

import worlds.up_pension as world
from munshi.task_factory import build_task_components
from worlds.up_pension.agents.default import build_graph

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

_COMPONENTS = build_task_components(
    world_module=world,
    scenarios_dir=SCENARIOS_DIR,
    graph_builder=build_graph,
    step_cap=80,
    cost_threshold_dollars=0.50,
)


@task
def up_pension() -> Task:
    return Task(**_COMPONENTS)
