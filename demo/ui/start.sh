#!/usr/bin/env bash
# Start the Munshi workbench UI locally.
# Tries ports 8000, 8001, 8002, ... until one is free.

set -e
cd "$(dirname "$0")"

for PORT in 8000 8001 8002 8003 8004 8005; do
  if ! lsof -i ":${PORT}" >/dev/null 2>&1; then
    echo
    echo "==> Munshi workbench starting at http://localhost:${PORT}"
    echo "==> Landing:   http://localhost:${PORT}/index.html"
    echo "==> Workbench: http://localhost:${PORT}/workbench.html"
    echo
    exec python3 -m http.server "${PORT}"
  fi
  echo "port ${PORT} busy, trying next..."
done

echo "all ports 8000-8005 busy; free one with: lsof -ti :8000 | xargs kill -9"
exit 1
