#!/usr/bin/env bash
# Run from your local machine to push code and restart the server on EC2.
# Usage: bash deploy/redeploy.sh [ec2-host] [key-path]
set -euo pipefail

HOST="${1:-51.21.191.238}"
KEY="${2:-$HOME/.ssh/bublet-key.pem}"
REMOTE_DIR="/home/ubuntu/munshi"

echo "==> Syncing code to $HOST"
rsync -az --exclude='.venv' --exclude='munshi.egg-info' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.git' --exclude='munshi.db' \
  -e "ssh -i $KEY -o StrictHostKeyChecking=no" \
  /Users/bubbles/Desktop/munshi/ "ubuntu@$HOST:$REMOTE_DIR/"

echo "==> Installing deps and restarting"
ssh -i "$KEY" "ubuntu@$HOST" "
  cd $REMOTE_DIR
  .venv/bin/pip install -q -e .
  sudo systemctl restart munshi
  sleep 2
  sudo systemctl status munshi --no-pager | head -20
  curl -s http://localhost:8000/health
"

echo ""
echo "==> Done. Backend: http://$HOST:8000"
