#!/usr/bin/env bash
# VeraCheck — Local Development Quick-Start
# Usage: ./scripts/dev.sh

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${CYAN}[VeraCheck]${NC} $1"; }
ok()  { echo -e "${GREEN}✓${NC} $1"; }
warn(){ echo -e "${YELLOW}⚠${NC}  $1"; }

log "Starting VeraCheck development environment..."

# 1. Check Python
python3 --version &>/dev/null || { echo "Python 3.9+ required"; exit 1; }
ok "Python found"

# 2. Check Node
node --version &>/dev/null || { echo "Node 18+ required"; exit 1; }
ok "Node found"

# 3. Backend setup
log "Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
  python3 -m venv venv
  ok "Virtual environment created"
fi

source venv/bin/activate
pip install -q -r requirements.txt
ok "Backend dependencies installed"

# Copy env if not exists
[ -f .env ] || cp .env.example .env && ok ".env created from example"

# 4. Start Redis (if available) or warn
if command -v redis-server &>/dev/null; then
  redis-server --daemonize yes --port 6379 2>/dev/null || true
  ok "Redis started"
else
  warn "Redis not found — running with in-memory cache fallback"
fi

# 5. Start backend in background
log "Starting FastAPI backend on :8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
ok "Backend PID: $BACKEND_PID"

# 6. Frontend setup
cd ../frontend
log "Setting up frontend..."

if [ ! -d "node_modules" ]; then
  npm install
  ok "Frontend dependencies installed"
fi

[ -f .env.local ] || cp .env.local.example .env.local && ok ".env.local created"

# 7. Start frontend
log "Starting Next.js frontend on :3000..."
npm run dev &
FRONTEND_PID=$!
ok "Frontend PID: $FRONTEND_PID"

echo ""
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  VeraCheck is running!${NC}"
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "  Frontend: ${CYAN}http://localhost:3000${NC}"
echo -e "  Backend:  ${CYAN}http://localhost:8000${NC}"
echo -e "  API Docs: ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo "Press Ctrl+C to stop all services."

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
