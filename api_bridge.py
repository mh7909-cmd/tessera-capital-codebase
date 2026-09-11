import os
import sys
import warnings

# Global Silence for demo-grade output
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

import sys
import json
import asyncio
import subprocess
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import re
from datetime import datetime

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
subscribers = set()
active_process = None
# MiroFish state tracking for UI persistence
mirofish_sim_done = False
current_miro_project_id = None
current_miro_simulation_id = None
current_miro_max_rounds = 10
ic_done = False
SESSION_START_TIME = None

async def run_alpha_flow(ticker=None, demo=False):
    global active_process
    """Starts the orchestrator and streams its output to the queue."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # Run the FULL end-to-end pipeline from the root
    cmd = f"{sys.executable} -u alpha_flow.py"
    if demo:
        cmd += " --demo"
    else:
        # Only pass --ticker if explicitly provided; no ticker = full screener mode
        _ticker = ticker or env.get("TEST_TICKER")
        if _ticker:
            cmd += f" --ticker \"{_ticker}\""

    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    active_process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=root_dir,
        env=env
    )

    async for line in active_process.stdout:
        decoded_line = line.decode().strip()
        if not decoded_line:
            continue
            
        # 🛡️ NOISE SCRUBBING: Strip ANSI codes (e.g., [38;5;10m)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        decoded_line = ansi_escape.sub('', decoded_line)

        # 🛡️ INSTITUTIONAL FILTER: Drop non-professional noise
        # This list targets specific developer metadata, ASCII art, and status polling.
        NOISE_BLOCKLIST = [
            "⌨️ [KINETIC]", "[nltk_data]", "already up-to-date", "Software Version", "Data Update Time",
            "|  _  \\", "| | | |", "|___/ \\___|", "____", "|  _|", # ASCII Art fragments
            "--- INSTITUTIONAL", ":: Data Update", ":: Software",
            "[SYSTEM] Connecting", "[SYSTEM] Commencing", "Loading universe",
            "(This may take several minutes)", "Fetched 503 S&P 500",
            "[DATALAKE]", "[SCANNING", "Securing connection to datalake"
        ]
        
        # Aggressive ASCII Art Detection: Filter out lines with excessive box-drawing or pattern characters
        if any(noise in decoded_line for noise in NOISE_BLOCKLIST):
            continue
            
        if decoded_line.count('|') > 3 or decoded_line.count('_') > 5 or decoded_line.count('\\') > 3:
            continue

        # Check for machine-readable UI signals
        if decoded_line.startswith("::UI_SIGNAL::"):
            try:
                signal_json = decoded_line.replace("::UI_SIGNAL::", "").strip()
                signal_data = json.loads(signal_json)
                
                # Update global state for fresh connections
                if signal_data.get("type") == "TAB_FOCUS":
                    global current_active_ticker, current_active_gid, current_active_sheet_id
                    current_active_ticker = signal_data.get("ticker")
                    current_active_gid = signal_data.get("gid", "0")
                    if signal_data.get("sheet_id"):
                        current_active_sheet_id = signal_data.get("sheet_id")
                
                await broadcast({"event": "signal", "data": signal_data})
            except Exception as e:
                print(f"ERROR PARSING SIGNAL: {e}")
        else:
            # Regular log line
            theatrical_time = get_theatrical_time()
            
            # Check if the line already starts with a timestamp HH:MM:SS
            timestamp_pattern = re.compile(r'^\d{2}:\d{2}:\d{2}')
            if not timestamp_pattern.match(decoded_line):
                final_log = f"{theatrical_time}\n{decoded_line}"
            else:
                final_log = decoded_line
                
            await broadcast({"event": "log", "data": final_log})
            
    await active_process.wait()
    active_process = None
    # Wait 15s to allow the UI to finish popping the final round cards (telemetry queue processing)
    await asyncio.sleep(15)
    await broadcast({"event": "signal", "data": {"type": "PHASE_CHANGE", "phase": "DONE", "msg": "Full Audit Cycle Complete"}})

def get_theatrical_time():
    """
    Returns the current mission time based on a 04:53:00 AM start,
    relative to when the session actually began.
    """
    from datetime import datetime, timedelta
    global SESSION_START_TIME
    
    # Baseline for all Hollywood events
    mission_start = datetime.now().replace(hour=4, minute=53, second=0, microsecond=0)
    
    if SESSION_START_TIME is None:
        return mission_start.strftime("%H:%M:%S.000")
    
    # Calculate elapsed time since simulation start
    elapsed = datetime.now() - SESSION_START_TIME
    theatrical_now = mission_start + elapsed
    return theatrical_now.strftime("%H:%M:%S.%f")[:-3]

async def broadcast(message):
    """Sends a message to all connected clients."""
    if not subscribers:
        return
    
    msg_json = json.dumps(message)
    # Use list() to avoid 'Set changed size during iteration' errors
    for q in list(subscribers):
        try:
            await q.put(msg_json)
        except:
            subscribers.remove(q)

@app.get("/events")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint to stream logs/signals to the browser."""
    client_queue = asyncio.Queue()
    subscribers.add(client_queue)
    print(f"🔌 New SSE Client Connected. Total subscribers: {len(subscribers)}")
    
    # Send current MiroFish context if active
    if current_miro_project_id:
        miro_signal = {
            "event": "signal",
            "data": {
                "type": "MIROFISH_SIM_READY",
                "project_id": current_miro_project_id,
                "simulation_id": current_miro_simulation_id or "",
                "max_rounds": current_miro_max_rounds
            }
        }
        await client_queue.put(json.dumps(miro_signal))

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    item = await asyncio.wait_for(client_queue.get(), timeout=1.0)
                    yield f"data: {item}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            subscribers.remove(client_queue)
                
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/launch")
async def launch_audit(request: Request):
    global active_process
    """API endpoint to trigger the full market diligence workflow."""
    
    # Parse potential ticker target
    ticker = None
    try:
        body = await request.json()
        ticker = body.get("ticker")
    except:
        pass # Optional body

    # 🚨 KILL SWITCH: Terminate ghost processes
    if active_process is not None:
        print("Terminating existing pipeline run...")
        try:
            active_process.terminate()
            await active_process.wait()
        except:
            pass
        active_process = None

    # Clear state for fresh run
    global current_active_ticker, current_active_gid, current_active_sheet_id, mirofish_sim_done
    current_active_ticker = None
    current_active_gid = "0"
    current_active_sheet_id = None
    mirofish_sim_done = False  # Reset so webhook polling works cleanly on new run
        
    asyncio.create_task(run_alpha_flow(ticker=ticker))
    return {"status": "Flow Launched Successfully", "target": ticker or "GLOBAL"}

@app.post("/reset")
async def reset_bridge_state():
    """Polled by orchestrator to clear state for a fresh run."""
    global current_active_ticker, current_active_gid, current_active_sheet_id, mirofish_sim_done, ic_done, SESSION_START_TIME
    current_active_ticker = None
    current_active_gid = "0"
    current_active_sheet_id = None
    mirofish_sim_done = False
    ic_done = False
    SESSION_START_TIME = datetime.now()
    print("🧹 [BRIDGE] State cleared for new simulation run (Time Reset to 04:53:00).")
    return {"status": "Bridge state reset"}

@app.post("/signal")
async def receive_external_signal(request: Request):
    """Allows external scripts to broadcast machine-readable signals to the frontend."""
    global mirofish_sim_done, ic_done, current_miro_project_id, current_miro_simulation_id, current_miro_max_rounds
    try:
        signal_data = await request.json()
        print(f"📡 External Signal Received: {signal_data.get('type')}")

        # Track MiroFish simulation completion so webhook_server can poll instead of sleeping
        if signal_data.get("type") == "MIROFISH_SIM_DONE":
            mirofish_sim_done = True
            print("✅ [BRIDGE] MiroFish simulation marked complete.")

        if signal_data.get("type") == "FINAL_AGENTS_DONE":
            ic_done = True
            print("✅ [BRIDGE] Final Agents IC marked complete.")

        # Persist MiroFish context so UI refreshes catch up
        if signal_data.get("type") in ["MIROFISH_LIVE", "MIROFISH_SIM_READY"]:
            current_miro_project_id = signal_data.get("project_id")
            current_miro_simulation_id = signal_data.get("simulation_id")
            current_miro_max_rounds = signal_data.get("max_rounds", current_miro_max_rounds)
            print(f"📌 [BRIDGE] Persisting MiroFish context: proj={current_miro_project_id}, sim={current_miro_simulation_id}, max={current_miro_max_rounds}")

        await broadcast({"event": "signal", "data": signal_data})
        return {"status": "Signal Broadcasted"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}

@app.get("/mirofish-status")
async def get_mirofish_status():
    """Polled by webhook_server.py to know when MiroFish simulation tweets are done."""
    return {"done": mirofish_sim_done, "ic_done": ic_done}

@app.get("/ic-status")
async def get_ic_status():
    """Polled by alpha_flow.py to know when the full show is over."""
    return {"done": ic_done}

@app.post("/log")
async def receive_external_log(request: Request):
    """Allows external scripts to stream log text directly to the UI."""
    try:
        body = await request.json()
        log_msg = body.get("msg", "")
        if log_msg:
            # Prepend theatrical time if not present
            theatrical_time = get_theatrical_time()
            timestamp_pattern = re.compile(r'^\d{2}:\d{2}:\d{2}')
            if not timestamp_pattern.match(log_msg):
                final_log = f"{theatrical_time}\n{log_msg}"
            else:
                final_log = log_msg
            await broadcast({"event": "log", "data": final_log})
        return {"status": "Log Broadcasted"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
