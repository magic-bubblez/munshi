#!/usr/bin/env bash
# Munshi — UP Pension testbed runner
#
# Runs the agent against the demo scenario, prints the scoreboard, and opens
# the Inspect View replay UI in your browser.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  echo "no .venv found — run: python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [[ ! -f .env ]]; then
  echo "no .env found — copy .env.example to .env and set ANTHROPIC_API_KEY"
  exit 1
fi

echo
echo "==> Running the testbed against the UP pension world"
echo
inspect eval worlds/up_pension/task.py --model anthropic/claude-sonnet-4-6

echo
echo "==> Opening the replay UI (Ctrl+C to stop the viewer)"
echo
inspect view
