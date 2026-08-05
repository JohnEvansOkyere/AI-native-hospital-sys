#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  ██╗   ██╗███████╗██╗      ██████╗ ██╗  ██╗ █████╗  ██████╗ █████╗ ██████╗ ███████╗"
echo "  ██║   ██║██╔════╝██║     ██╔═══██╗╚██╗██╔╝██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝"
echo "  ██║   ██║█████╗  ██║     ██║   ██║ ╚███╔╝ ███████║██║     ███████║██████╔╝█████╗  "
echo "  ╚██╗ ██╔╝██╔══╝  ██║     ██║   ██║ ██╔██╗ ██╔══██║██║     ██╔══██║██╔══██╗██╔══╝  "
echo "   ╚████╔╝ ███████╗███████╗╚██████╔╝██╔╝ ██╗██║  ██║╚██████╗██║  ██║██║  ██║███████╗"
echo "    ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝"
echo ""
echo "  Patient Engagement Platform · Demo Mode"
echo ""

# ── Python backend ────────────────────────────────────────────────────────────
cd "$ROOT/backend"

if [ ! -d ".venv" ]; then
  echo "  → Setting up Python environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements-local.txt

# Copy .env if not present
if [ -f "$ROOT/.env" ]; then
  cp "$ROOT/.env" "$ROOT/backend/.env"
fi

echo "  → Starting API server on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# ── Frontend ──────────────────────────────────────────────────────────────────
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  echo "  → Installing frontend dependencies..."
  npm install --silent
fi

echo "  → Starting dashboard on http://localhost:5173"
npm run dev &
VITE_PID=$!

echo ""
echo "  ✅ VeloxaCare is running!"
echo ""
echo "     Dashboard  →  http://localhost:5173"
echo "     API        →  http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

cleanup() {
  kill $API_PID $VITE_PID 2>/dev/null || true
  echo "  Stopped."
}
trap cleanup EXIT INT TERM

wait
