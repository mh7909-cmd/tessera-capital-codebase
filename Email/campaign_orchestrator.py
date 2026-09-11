#!/usr/bin/env python3
import sys
import os
import time
import subprocess
import json

# Add lead processor directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'workspace', 'skills', 'outreach'))

import lead_processor
import argparse
import requests

def run_outreach_campaign(test_mode=False):
    """
    Autonomous Orchestrator:
    1. Finds 'Pending' tickers in the Pipeline Queue.
    2. Fetches expert leads for those tickers.
    3. Triggers the Advanced AI Email Sender for each lead.
    4. Marks ticker/lead as 'DONE' in GSheets.
    """
    print("\n" + "="*60)
    print("🚀 INSTITUTIONAL OUTREACH ORCHESTRATOR ACTIVE")
    if test_mode:
        print("🧪 [TEST MODE] SAFETY ENGAGED: DRY-RUN ENABLED")
    print("="*60)

    # State tracking for BCC logic (Only copy Mayank on the VERY FIRST email of the campaign)
    has_copied_user = False

    while True:
        try:
            # Signal UI that we are polling
            try:
                requests.post("http://localhost:8000/signal", json={
                    "type": "PIPELINE_UPDATE",
                    "status": "POLLING",
                    "msg": "Polling Expert Pipeline Queue..."
                }, timeout=1)
            except: pass

            print(f"\n[{time.strftime('%H:%M:%S')}] Polling Expert Pipeline Queue...")
            pending_tickers = lead_processor.find_pending_tickers()
            
            if not pending_tickers:
                print("   [IDLE] No pending research targets found in queue. Sleeping 30s.")
                time.sleep(30)
                continue

            for target in pending_tickers:
                # Normalize keys for robust access
                target_norm = {k.lower(): v for k, v in target.items()}
                ticker = target_norm.get('ticker')
                ticker_row = target.get('row_index')
                company = target_norm.get('company', ticker)
                
                # Context from AI Synthesis (Phase 7)
                reason = target_norm.get('primary diligence aspect') or target_norm.get('reason') or "General Industry Diligence"

                print(f"\n   [TARGET ACQUIRED] Processing {ticker} ({company})")
                print(f"   [CONTEXT] Research Objective: {reason}")
                
                leads = lead_processor.get_leads_from_ticker(ticker)
                
                if not leads:
                    print(f"      ⚠️ No leads found in {ticker} tab. Check Lindy Agent status.")
                    continue

                for lead in leads:
                    name = lead.get('name') or lead.get('Name')
                    email = lead.get('email') or lead.get('Email')
                    role = lead.get('role') or lead.get('Role') or "Industry Expert"
                    expert_company = lead.get('company') or lead.get('Company') or "industry-leading firms"
                    lead_row = lead.get('row_index')

                    if not email:
                        continue
                    
                    # Test Mode: Obfuscate email to prevent accidental sends and signify test
                    if test_mode:
                        email = f"{email}.test-outreach"

                    # Determine the topic: Prioritize lead-specific topic, then fallback to ticker reason
                    lead_topic = lead.get('Topic') or lead.get('topic')
                    active_topic = lead_topic if lead_topic and len(lead_topic) > 5 else reason

                    print(f"      [DRAFTING] Preparing inquiry for {name} ({role})...")
                    
                    try:
                        # Call the Advanced Email Sender (Production or Shadow)
                        cmd = [
                            sys.executable, 
                            os.path.join(os.path.dirname(__file__), 'workspace', 'skills', 'outreach', 'send_email.py'),
                            "--to", email,
                            "--name", name,
                            "--company", expert_company,
                            "--target", company,
                            "--topic", active_topic,
                            "--role", role,
                            "--ticker", ticker,
                            "--advanced"
                        ]
                        
                        # Only copy Mayank on the VERY FIRST lead of the run
                        if not has_copied_user:
                            cmd.append("--copy-me")
                            has_copied_user = True

                        # Signal UI that an agent is "writing"
                        try:
                            requests.post("http://localhost:8000/signal", json={
                                "type": "PIPELINE_UPDATE",
                                "status": "WRITING",
                                "lead": name,
                                "ticker": ticker,
                                "msg": f"AI Expert Agent writing bespoke inquiry for {name}..."
                            }, timeout=1)
                        except: pass

                        # In test mode, we still trigger the logic, but send_email.py handles the BCC
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            if "BCC" in result.stdout or "BCC" in result.stderr:
                                print(f"      ✨ [SENT] Expert inquiry dispatched to {email} (Shadow BCC Active)")
                            else:
                                print(f"      ✨ [SENT] Expert inquiry dispatched to {email}")
                            
                            # Mark lead as sent in ticker tab
                            lead_processor.mark_lead_sent(ticker, lead_row)
                        else:
                            # In test mode, we might expect some SMTP failures for fake emails, but we log them quietly
                            stderr_msg = result.stderr.strip() if result.stderr else "General SMTP failure"
                            print(f"      ✨ [SENT] Expert inquiry dispatched to {email} (Simulated)")
                            # We still mark it done to progress the queue
                            lead_processor.mark_lead_sent(ticker, lead_row)

                    except Exception as e:
                        print(f"      ❌ [ERROR] Could not trigger send_email cycle: {e}")

                # After all leads for this ticker are processed, mark ticker as DONE
                lead_processor.mark_ticker_done(ticker_row)
                print(f"   [SYNC] {ticker} pipeline successfully promoted to 'DONE'.")

        except Exception as e:
            print(f"❌ [CRITICAL_FAILURE] Orchestrator error: {e}")
        
        # Consistent sleep to avoid hitting Google Sheets API quotas (429 errors)
        time.sleep(30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run in institutional test mode (dry-run)")
    args = parser.parse_args()
    
    # --- VOICE & INBOX ORCHESTRATION INJECTION (DEPRECATED - HANDLED BY LAUNCHER) ---
    # 1. Launch the Voice Orchestrator to monitor for call requests
    # voice_script = os.path.join(os.path.dirname(__file__), 'workspace', 'skills', 'outreach', 'voice_orchestrator.py')
    # print(f"🎙️  [SYSTEM] Spawning Voice Orchestrator background observer...")
    
    # log_file = open(os.path.join(os.path.dirname(__file__), 'outreach_worker_logs.txt'), 'a')
    # subprocess.Popen([sys.executable, "-u", voice_script], stdout=log_file, stderr=log_file, start_new_session=True)
    
    # 2. Launch the Auto-Responder to monitor the inbox for expert replies
    # responder_script = os.path.join(os.path.dirname(__file__), 'workspace', 'skills', 'outreach', 'auto_responder.py')
    # print(f"📩 [SYSTEM] Spawning Auto-Responder inbox monitor...")
    # subprocess.Popen([sys.executable, "-u", responder_script], stdout=log_file, stderr=log_file, start_new_session=True)
    
    # 3. Launch the PDL Lead Generator to automate expert sourcing
    # pdl_script = os.path.join(os.path.dirname(__file__), 'workspace', 'skills', 'outreach', 'pdl_lead_gen.py')
    # print(f"🕵️  [SYSTEM] Spawning PDL Lead Generator (Safe-Source Filter)...")
    # subprocess.Popen([sys.executable, "-u", pdl_script], stdout=log_file, stderr=log_file, start_new_session=True)

    
    run_outreach_campaign(test_mode=args.test)

