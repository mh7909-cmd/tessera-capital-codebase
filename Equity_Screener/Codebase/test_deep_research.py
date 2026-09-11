import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from equity_screener_agent import EquityScreenerAgent
from data_ingestion import YFinanceProvider
import pandas as pd

def test_deep_research_funnel():
    print("🚀 Running Institutional Deep Research Smoke Test...")
    
    # 1. Fetch small quant sample
    provider = YFinanceProvider(max_workers=2)
    test_tickers = ["MSFT"] # MSFT usually has full history
    
    print(f"\n[Stage 1] Quant Screening for {test_tickers}...")
    df = provider.get_universe_from_list(test_tickers, min_mcap=0, max_mcap=10e12)
    
    if df.empty:
        print("❌ Could not fetch data for test tickers.")
        return

    # Fix sector mismatch for Yahoo Finance
    df['sector'] = "Information Technology"

    # 2. Run Hybrid Funnel via Agent
    print("\n[Stage 2] Initializing Agent with Deep Research ENABLED...")
    agent = EquityScreenerAgent(min_mcap=0, max_mcap=10e12, deep_research=True)
    agent.universe = df
    
    # We only want to run for Information Technology
    sector = "Information Technology"
    print(f"\n[Stage 3] Executing Multi-Stage Funnel for {sector}...")
    
    screener = agent._get_sector_screener(sector)
    # The screener will now:
    # 1. Broad Quant
    # 2. Deep Quant (Defeat Beta: Transcripts, WACC, Insider)
    # 3. Deep Qual (Gemma 4 + Transcripts)
    
    results = screener.run_sector_funnel()
    
    print("\n" + "="*80)
    print("DEEP RESEARCH RESULTS SUMMARY")
    print("="*80)
    
    if not results.empty:
        row = results.iloc[0]
        print(f"Ticker: {row['ticker']}")
        print(f"Qualitative Sentiment: {row.get('qual_sentiment', 'N/A')}")
        print(f"Sentiment Drift: {row.get('sentiment_drift', 'N/A')}")
        print(f"ROIC: {row.get('roic', 'N/A')}")
        print(f"WACC: {row.get('wacc', 'N/A')}")
        print(f"DCF Fair Price: {row.get('fair_price', 'N/A')}")
        upside_val = row.get('dcf_upside', 0)
        upside_val = upside_val if upside_val is not None else 0
        print(f"Upside %: {float(upside_val)*100:.1f}%")
        print(f"Insider Buying: {row.get('insider_buying', 'N/A')}")
        print(f"Beta (5y): {row.get('beta_5y', 'N/A')}")
        print(f"Composite Rank: {row.get('composite_score', 'N/A'):.2f}")
        print("-" * 40)
        print(f"AI Institutional Summary:\n{row.get('ai_summary', 'N/A')}")
        print("-" * 40)
        print("✅ SUCCESS: Institutional Hybrid Funnel verified.")
    else:
        print("❌ Funnel completed but no candidates selected. Check constraints.")

if __name__ == "__main__":
    test_deep_research_funnel()
