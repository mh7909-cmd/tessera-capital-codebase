import os
import sys
import json
import time
import urllib.request
import imaplib
import email
import re
from email.mime.text import MIMEText
from email.utils import parseaddr
import smtplib
from datetime import datetime
from dotenv import load_dotenv

# Load workspace root .env for credentials
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))

# Constants
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# Pull from Email/.env explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
EMAIL_USER = os.environ.get("GMAIL_USER", "tesseracapital@gmail.com")
EMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD", "hlfy rctn bqep etnd")
DEMO_CALL_NUMBER = "+16462625452"

# Debug print that flushes
def dprint(msg):
    print(msg, flush=True)

def extract_phone_number(text):
    if not text: return None
    pattern = r'(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
    match = re.search(pattern, text)
    if match:
        clean = re.sub(r'[-.\s\(\)]', '', match.group(1))
        if not (clean.startswith('+1') or clean.startswith('1')):
             clean = '+1' + clean if not clean.startswith('+') else clean
        elif clean.startswith('1') and not clean.startswith('+'):
             clean = '+' + clean
        return clean
    return None

def detect_call_intent(text):
    if not text: return False
    text_lower = text.lower()
    
    triggers = [
        "call me", "speak now", "talk now", "ring me", "phone me", 
        "hey can u call", "hey can you call", "call now", "give me a call",
        "let's talk", "let's speak", "reach out", "ring now", "up for a call",
        "available now", "available to talk", "call me now",
        "yes", "sure", "ok", "fine", "cool", "yeah", "yep", "certainly", "absolutely"
    ]
    
    # Direct keyword match
    if any(t in text_lower for t in triggers):
        return True
        
    # Contextual matches
    has_call_term = any(t in text_lower for t in ["call", "phone", "talk", "ring", "speak"])
    has_now = any(t in text_lower for t in ["now", "right away", "asap", "immediately", "soon"])
    
    if has_call_term and (has_now or "you" in text_lower or "u " in text_lower):
        return True
        
    return False

def pull_and_respond():
    # Persistent connection strategy for demo-grade reliability
    connected = False
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            dprint(f"[{datetime.now().strftime('%H:%M:%S')}] Syncing with Institutional Inbox...")
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=10)
            mail.login(EMAIL_USER, EMAIL_PASS)
            connected = True
            break
        except Exception as e:
            dprint(f"   ⚠️ Connection flickered (Retry {attempt+1}/2)...")
            time.sleep(1)
            
    if not connected:
        return

    try:
        mail.select("inbox")
        # Diagnostic: Check the flags on the last 3 messages to see why they aren't 'UNSEEN'
        status, all_response = mail.search(None, 'ALL')
        if status == 'OK' and all_response[0]:
            last_nums = all_response[0].split()[-3:]
            for num in last_nums:
                res, flag_data = mail.fetch(num, '(FLAGS)')
                dprint(f"DEBUG: Message {num.decode()} Flags: {flag_data[0].decode()}")

        status, response = mail.search(None, '(UNSEEN)')
        
        num_unseen = len(response[0].split()) if response[0] else 0
        if num_unseen > 0:
            dprint(f"🔎 Found {num_unseen} UNSEEN emails.")
            
        if status != 'OK' or not response[0]:
            mail.logout()
            return

        for num in response[0].split()[::-1]:
            # Always mark SEEN so we don't process it twice
            mail.store(num, '+FLAGS', '\\Seen')
            
            status, data = mail.fetch(num, '(RFC822)')
            if status != 'OK': continue
            
            msg = email.message_from_bytes(data[0][1])
            sender_email = parseaddr(msg['From'])[1]
            subject = msg['Subject']
            dprint(f"📩 Processing UNSEEN email from: {sender_email} | Subject: {subject}")
            
            # [REMOVED SELF-FILTER FOR DEMO TESTING]
            # if sender_email == EMAIL_USER: continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

            if not body: continue

            if detect_call_intent(body):
                extracted_num = extract_phone_number(body)
                target_num = extracted_num or DEMO_CALL_NUMBER
                
                # Retrieve context from campaign tracker
                dprint(f"🎯 INTENT MATCHED: Requesting call to {target_num}")
                
                try:
                    # Derive paths relative to this file to support any working directory
                    _this_dir = os.path.dirname(os.path.abspath(__file__))
                    VOICE_DIR = os.path.normpath(os.path.join(_this_dir, "../../../../voiceagent"))
                    EMAIL_DIR = _this_dir
                    if VOICE_DIR not in sys.path: sys.path.insert(0, VOICE_DIR)
                    if EMAIL_DIR not in sys.path: sys.path.insert(0, EMAIL_DIR)
                    
                    from phone import trigger_outbound_call
                    import campaign_tracker
                    
                    # Try to find the expert's original firm and the ticker from the state
                    expert_firm = "your firm"
                    diligence_ticker = "FLY"
                    
                    # Search by sender email in state
                    state = campaign_tracker.load_state()
                    for thread_id, thread in state.get("threads", {}).items():
                        if thread.get("to_email") == sender_email:
                            expert_firm = thread.get("company", expert_firm)
                            diligence_ticker = thread.get("ticker", diligence_ticker)
                            break
                    
                    dprint(f"📞 Launching VAPI call sequence for {diligence_ticker}...")
                    result = trigger_outbound_call(
                        target_num,
                        lead_name="Shubhanker",
                        company=expert_firm,
                        email_context=body,
                    )
                    if result:
                        dprint(f"   ✅ VAPI SUCCESS — call initiated.")
                    else:
                        dprint(f"   ❌ VAPI returned no result — check phone.py logs.")
                except Exception as e:
                    dprint(f"   ❌ VAPI Error: {e}")
            
            # Always mark seen
            mail.store(num, '+FLAGS', '\\Seen')

        mail.logout()
    except Exception as e:
        dprint(f"   ⚠️ IMAP Error: {e}")

if __name__ == "__main__":
    dprint("🚀 [DEMO_MODE] Auto-Responder listening for 'Call Me' triggers...")
    while True:
        try:
            pull_and_respond()
        except Exception as e:
            dprint(f"   ⚠️ Polling Loop Error: {e}")
        time.sleep(10) # 10s polling for high-speed demo response
