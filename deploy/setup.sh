#!/usr/bin/env bash
# Run once on a fresh EC2 Ubuntu instance.
# Usage: bash deploy/setup.sh
set -euo pipefail

REPO_DIR="$HOME/munshi"

echo "==> Installing system dependencies"
sudo apt-get update -q
sudo apt-get install -y python3.11 python3.11-venv python3-pip git

echo "==> Cloning / pulling repo"
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" pull
else
  git clone https://github.com/magic-bubblez/munshi.git "$REPO_DIR"
fi

echo "==> Creating virtual environment"
python3.11 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install -q --upgrade pip
"$REPO_DIR/.venv/bin/pip" install -q -e "$REPO_DIR"

echo "==> Installing systemd service"
sudo cp "$REPO_DIR/deploy/munshi.service" /etc/systemd/system/munshi.service
sudo systemctl daemon-reload
sudo systemctl enable munshi
sudo systemctl restart munshi

echo "==> Done. Check status with: sudo systemctl status munshi"
echo "    Tail logs with:           sudo journalctl -u munshi -f"
