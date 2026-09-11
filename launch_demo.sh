#!/bin/bash

# Tessera Capital - Institutional Demo Launcher
# This script terminates existing processes and launches the full stack.

echo "🛑 Terminating existing services on ports 8000, 8765, 3000, 3001, 5001..."
lsof -i :8000 -i :8765 -i :3000 -i :3001 -i :5001 -t | xargs kill -9 2>/dev/null || true

echo "🚀 Launching API Bridge (Port 8000)..."
nohup python3 api_bridge.py > bridge.log 2>&1 &

echo "🚀 Launching Voice Webhook Server (Port 8765)..."
nohup python3 voiceagent/webhook_server.py > webhook.log 2>&1 &

echo "🚀 Launching MiroFish Backend (Port 5001)..."
cd MiroFish/backend
nohup python3 run.py > backend.log 2>&1 &
cd ../..

echo "🚀 Launching MiroFish Frontend (Port 3001)..."
cd MiroFish/frontend
nohup npm run dev -- --port 3001 > frontend_miro.log 2>&1 &
cd ../..

echo "🚀 Launching Main Research Dashboard (Port 3000)..."
cd frontend
nohup npm run dev > frontend_main.log 2>&1 &
cd ..

echo "🚀 Launching Campaign Orchestrator (Polling Mode)..."
nohup python3 Email/campaign_orchestrator.py --test > outreach.log 2>&1 &

echo "🚀 Launching Voice Orchestrator (Intent Monitor)..."
nohup python3 Email/workspace/skills/outreach/voice_orchestrator.py > voice_monitor.log 2>&1 &

echo "=========================================================="
echo "✅ ALL SYSTEMS OPERATIONAL"
echo "🖥️  Main UI: http://localhost:3000"
echo "🖥️  MiroFish: http://localhost:3001"
echo "📊 Bridge: http://localhost:8000"
echo "=========================================================="
echo "Use 'tail -f bridge.log' to monitor real-time signals."
