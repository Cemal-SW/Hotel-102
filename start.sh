#!/usr/bin/env bash
# Serve this site locally. Run: ./start.sh   or   bash start.sh
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"

if ! command -v python3 &>/dev/null; then
  echo "python3 is required but was not found. Install Python 3 or use: npx serve ."
  exit 1
fi

echo "Starting server at http://localhost:${PORT}"
echo "Press Ctrl+C to stop."
(sleep 0.7 && open "http://localhost:${PORT}" 2>/dev/null) &
exec python3 -m http.server "$PORT"
