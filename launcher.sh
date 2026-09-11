#!/bin/bash

# Resolve the repo root relative to this script regardless of cwd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill any existing processes to avoid port conflicts and duplicates
echo "🧹 Cleaning up existing processes..."
pkill -f webhook_server.py
pkill -f campaign_orchestrator.py
pkill -f auto_responder.py
pkill -f voice_orchestrator.py
pkill -f pdl_lead_gen.py
pkill -f api_bridge.py
pkill -f "MiroFish/backend/run.py"
lsof -ti:3001,5001,8000,8765 | xargs kill -9 2>/dev/null

# Clear old MiroFish project data so iframe doesn't auto-redirect to stale reports
echo "🗑️  Clearing old MiroFish simulation data..."
rm -rf "$SCRIPT_DIR/MiroFish/backend/uploads/projects/"*
rm -f "$SCRIPT_DIR/MiroFish/backend/scripts/twitter_simulation.db"
echo "   ✅ MiroFish slate clean."

# --- CORE SERVICES ---
echo "🎙️ Starting Webhook Server on port 8765..."
cd "$SCRIPT_DIR/voiceagent"
PYTHONUNBUFFERED=1 python3 -u webhook_server.py > "$SCRIPT_DIR/webhook_server.log" 2>&1 &

echo "🌉 Starting Signal Bridge on port 8000..."
cd "$SCRIPT_DIR"
python3 api_bridge.py > "$SCRIPT_DIR/bridge.log" 2>&1 &

# --- MIROFISH STACK ---
echo "🐠 Starting MiroFish Backend on port 5001..."
cd "$SCRIPT_DIR/MiroFish/backend"
.venv/bin/python run.py > "$SCRIPT_DIR/mirofish_backend.log" 2>&1 &


# --- OUTREACH AGENTS ---
echo "🚀 Starting Institutional Outreach Orchestrator..."
cd "$SCRIPT_DIR/Email"
python3 -u campaign_orchestrator.py > "$SCRIPT_DIR/orchestrator.log" 2>&1 &

echo "📬 Starting Auto-Responder (inbox listener)..."
cd "$SCRIPT_DIR/Email/workspace/skills/outreach"
python3 -u auto_responder.py > "$SCRIPT_DIR/auto_responder.log" 2>&1 &

echo "🎙️  Starting Voice Orchestrator (call listener)..."
cd "$SCRIPT_DIR/Email/workspace/skills/outreach"
python3 -u voice_orchestrator.py >> "$SCRIPT_DIR/orchestrator.log" 2>&1 &

echo "🕵️  Starting PDL Lead Generator (sourcing agent)..."
cd "$SCRIPT_DIR/Email/workspace/skills/outreach"
python3 -u pdl_lead_gen.py >> "$SCRIPT_DIR/orchestrator.log" 2>&1 &

echo "✅ All systems active."
echo "--------------------------------------------------"
echo "1. Webhook Server: http://127.0.0.1:8765"
echo "2. MiroFish UI:    http://127.0.0.1:3001"
echo "3. Signal Bridge:  http://127.0.0.1:8000"
echo "4. Ensure ngrok is running: 'ngrok http 8765'"
echo "--------------------------------------------------"
