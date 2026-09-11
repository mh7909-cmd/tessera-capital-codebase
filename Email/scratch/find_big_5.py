#!/usr/bin/env python3
import os
import sys
import json
import requests
from dotenv import load_dotenv

# Import the actual logic from our production script
sys.path.append('/Users/mayankhinduja/Desktop/Demo/Email/workspace/skills/outreach')
import pdl_lead_gen

def fetch_top_5_verified():
    load_dotenv('/Users/mayankhinduja/Desktop/Demo/.env')
    
    ticker = "FOXA"
    company = "Fox Corporation"
    objective = "To further understand the impact of recent controversies on the company's revenue and to assess the potential risks associated with the Disney-FOXA merger."
    
    print(f"🚀 Finding the 'Big 5' for {ticker}...")
    
    # 1. LLM Strategy
    strategy = pdl_lead_gen.analyze_research_strategy_llm(company, objective)
    print(f"\n🧠 AI Sourcing Strategy:\n{json.dumps(strategy, indent=2)}")
    
    # 2. PDL Search (size=10 so we can pick the best 5)
    # We use the fallback key automatically if primary fails
    leads = pdl_lead_gen.execute_smart_search(company, strategy)
    
    if not leads:
        print("❌ No leads found.")
        return
        
    print(f"\n📊 Found {len(leads)} candidates. Manual Verification starting...\n")
    for l in leads[:5]:
        print(f"Candidate: {l['name']}")
        print(f"Current Role: {l['role']}")
        print(f"Company: {l['company']}")
        print(f"LinkedIn: {l['linkedin']}")
        print("-" * 20)

if __name__ == "__main__":
    fetch_top_5_verified()
