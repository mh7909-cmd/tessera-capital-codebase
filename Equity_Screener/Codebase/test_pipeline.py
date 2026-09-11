import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from equity_screener_agent import EquityScreenerAgent
from data_ingestion import YFinanceProvider
import pandas as pd

def test_nvidia_nim_screener():
    print("🚀 Running Production Smoke Test for NVIDIA NIM Llama 3.1 8B Equity Screener...")
    
    # 1. Test Quant Stage (Small Sample)
    print("\n--- Testing Quant Stage (Yahoo Finance) ---")
    provider = YFinanceProvider(max_workers=5)
    test_tickers = ["MSFT", "NVDA"]
    
    df = provider.get_universe_from_list(test_tickers, min_mcap=0, max_mcap=10e12)
    
    if df.empty:
        print("❌ Quant stage failed to return results.")
        return
        
    print(f"Quant stage returned {len(df)} stocks.")
    
    # 2. Test Agent & NVIDIA NIM Qualitative Stage
    print("\n--- Testing Agent & NVIDIA NIM Qualitative Stage ---")
    # This will use the default key hardcoded in AIService for this test
    agent = EquityScreenerAgent(min_mcap=0, max_mcap=10e12)
    agent.universe = df
    
    sample_sector = df['sector'].iloc[0]
    print(f"  Testing {sample_sector} Sector Screener with NVIDIA NIM...")
    
    try:
        screener = agent._get_sector_screener(sample_sector)
    except Exception:
        from equity_screener_agent import ITSectorScreener
        screener = ITSectorScreener(df[df['sector'] == sample_sector], ai_service=agent.ai_service)

    screener.universe = df[df['sector'] == sample_sector].copy()
    
    # Run the funnel - THIS WILL TRIGGER THE REAL NVIDIA API CALL
    results = screener.run_sector_funnel()
    
    print("\n--- Summary Results ---")
    if not results.empty:
        print(f"✅ Success! NVIDIA NIM returned research for {len(results)} candidates.")
        for idx, row in results.iterrows():
            print(f"\n[{row['ticker']}]")
            print(f"  Sentiment: {row.get('qual_sentiment', 'N/A')}")
            print(f"  AI Summary: {row.get('ai_summary', 'N/A')[:100]}...")
            print(f"  Is Sandbagging: {row.get('is_sandbagging', 'N/A')}")
    else:
        print(f"❌ Completed but identified 0 candidates in {sample_sector}.")

if __name__ == "__main__":
    test_nvidia_nim_screener()
