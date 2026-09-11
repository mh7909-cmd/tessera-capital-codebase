#!/usr/bin/env python3
import os
import sys
import json
import requests
from dotenv import load_dotenv

# Import the actual logic from our production script
sys.path.append('/Users/mayankhinduja/Desktop/Demo/Email/workspace/skills/outreach')
import pdl_lead_gen

def fetch_top_5_hybrid_ttwo():
    load_dotenv('/Users/mayankhinduja/Desktop/Demo/.env')
    
    ticker = "TTWO"
    company = "Take-Two Interactive"
    objective = "Analyze the efficiency of the Zynga acquisition integration and internal sentiment regarding the GTA VI development timeline, cost overruns, and margin impact."
    
    print(f"🚀 PIVOTING: Finding the 'Hybrid Big 5' for {ticker} (From Approved List)...")
    
    # 1. Hybrid LLM Strategy
    strategy = pdl_lead_gen.analyze_research_strategy_llm(company, objective)
    print(f"\n🧠 AI Hybrid Strategy:\n{json.dumps(strategy, indent=2)}")
    
    # 2. Execute Multi-Vector Search
    leads = pdl_lead_gen.execute_smart_search(company, strategy)
    
    if not leads:
        print("❌ No leads found.")
        return
        
    print(f"\n📊 Generated {len(leads)} Hybrid experts. Verification Roster:\n")
    for i, l in enumerate(leads):
        print(f"{i+1}. {l['name'].upper()}")
        print(f"   Role: {l['role']}")
        print(f"   Company: {l['company']}")
        print(f"   LinkedIn: {l['linkedin']}")
        print("-" * 30)

if __name__ == "__main__":
    fetch_top_5_hybrid_ttwo()
