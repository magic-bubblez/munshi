"""UP Pension world — public module surface required by Munshi's task factory.

The platform calls into these symbols by convention. Worlds fulfill the
contract by re-exporting; no inheritance, no registration calls.
"""

from worlds.up_pension.predicates import PREDICATES
from worlds.up_pension.schemas import PensionWorldState
from worlds.up_pension.seed import dump_state, seed
from worlds.up_pension.server import build_server
from worlds.up_pension.tools import make_tools

WORLD_NAME = "up_pension"
SCHEMAS = PensionWorldState
SEED = seed
TOOLS_FACTORY = make_tools
STATE_DUMPER = dump_state
SERVER_FACTORY = build_server
# PREDICATES is re-exported as-is

__all__ = [
    "WORLD_NAME",
    "SCHEMAS",
    "SEED",
    "TOOLS_FACTORY",
    "STATE_DUMPER",
    "SERVER_FACTORY",
    "PREDICATES",
]
