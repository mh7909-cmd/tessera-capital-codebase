#!/usr/bin/env python3
import os
import time
import json
import requests
import gspread
import urllib.request
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load env from root directory
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
load_dotenv(ENV_PATH)

STATE_FILE = os.path.join(os.path.dirname(__file__), 'voice_state.json')
VAPI_TRIGGER_URL = "http://localhost:8765/trigger-call"
DEMO_PHONE_NUMBER = "+16462625452"

def load_voice_state():
    if not os.path.exists(STATE_FILE):
        return {"called_threads": []}
    with open(STATE_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {"called_threads": []}

def save_voice_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def get_gspread_client():
    creds_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    if not os.path.exists(creds_file):
        root_creds_file = os.path.join(os.path.dirname(ENV_PATH), creds_file)
        if os.path.exists(root_creds_file):
            creds_file = root_creds_file
            
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    return gspread.authorize(creds)

def detect_call_intent_llm(text):
    """Uses LLM to classify if the expert is inviting a call."""
    if not text:
        return False
    
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        # Fallback to keyword matching if API is missing
        print("⚠️ Warning: NVIDIA_API_KEY missing. Falling back to keyword intent detection.")
        triggers = ["call me", "speak", "talk", "ring", "phone"]
        return any(t in text.lower() for t in triggers)

    prompt = f"""Classify the following expert reply. Does it contain an invitation or consent to have a phone call or conversation soon?
Expert Reply: "{text}"
Respond ONLY with 'YES' or 'NO'."""

    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    payload = {
        "model": "moonshotai/kimi-k2.5",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        })
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            answer = result['choices'][0]['message'].get('content', '').strip().upper()
            return "YES" in answer
    except Exception as e:
        print(f"❌ LLM Intent error: {e}")
        return False

def poll_and_trigger():
    print(f"🎙️ Voice Orchestrator (v2-LLM) started. Monitoring sheet for call requests...")
    client = get_gspread_client()
    sheet_id = os.environ.get("THREAD_SHEET_ID") or os.environ.get("GOOGLE_SHEET_ID")
    
    while True:
        try:
            spreadsheet = client.open_by_key(sheet_id)
            all_worksheets = spreadsheet.worksheets()
            
            state = load_voice_state()

            for worksheet in all_worksheets:
                # Initialize variables to avoid 'referenced before assignment' in case of skip
                records = []
                h_idx = -1
                id_idx = -1
                
                # Skip any tabs that might not be ticker threads
                if worksheet.title in ["Dashboard", "Pipeline Queue", "Sheet1"]:
                    continue
                    
                rows = worksheet.get_all_values()
                if len(rows) < 2:
                    continue
                    
                headers = rows[0]
                records = rows[1:]
                
                # Map headers to indices
                try:
                    h_idx = headers.index("Full_Thread_History")
                    id_idx = headers.index("Initial Message-ID")
                    name_idx = headers.index("Recipient Name")
                    comp_idx = headers.index("Company")
                    topic_idx = headers.index("Research Topic") if "Research Topic" in headers else -1
                except ValueError:
                    # This tab doesn't have the standard thread columns
                    continue
            
                for row in records:
                    thread_id = row[id_idx]
                    history = row[h_idx]
                    
                    if not thread_id or thread_id in state["called_threads"]:
                        continue
                    
                    # Logic: Find the most recent User message in the history
                    messages = [m.strip() for m in history.split('\n') if m.strip()]
                    last_user_msg = None
                    for msg in reversed(messages):
                        # Looking for the most recent message tagged as User
                        if "User:" in msg:
                            last_user_msg = msg
                            break
                    
                    if last_user_msg and detect_call_intent_llm(last_user_msg):
                        print(f"🚨 LLM Detected Call Invitation in: {last_user_msg}")
                        
                        topic = row[topic_idx] if topic_idx != -1 else "General Industry Analysis"
                        
                        # Trigger Vapi
                        payload = {
                            "phone_number": DEMO_PHONE_NUMBER,
                            "lead_name": row[name_idx],
                            "company": row[comp_idx],
                            "email_context": topic,
                            "ticker": worksheet.title
                        }
                        
                        try:
                            resp = requests.post(VAPI_TRIGGER_URL, json=payload)
                            if resp.status_code == 200:
                                print(f"✅ Call triggered successfully to {DEMO_PHONE_NUMBER}")
                                state["called_threads"].append(thread_id)
                                save_voice_state(state)
                            else:
                                print(f"❌ Vapi Trigger Failed: {resp.text}")
                        except Exception as e:
                            print(f"❌ Connection error to Webhook Server: {e}")
            
        except Exception as e:
            print(f"⚠️ Polling error: {e}")
            
        time.sleep(30)

if __name__ == "__main__":
    poll_and_trigger()
