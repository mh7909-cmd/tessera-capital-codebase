import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from equity_screener_agent import EquityScreenerAgent
from data_ingestion import YFinanceProvider
import pandas as pd
import argparse

def test_single_ticker(ticker):
    print(f"\n🚀 Running Single Ticker Deep-Dive Test for {ticker}...")
    
    # 1. Test Quant Stage (Yahoo Finance)
    print("\n--- [Step 1] Fetching Quantitative Data (Yahoo Finance) ---")
    provider = YFinanceProvider()
    
    # Don't filter by market cap for a direct test
    df = provider.get_universe_from_list([ticker], min_mcap=0, max_mcap=999e12)
    
    if df.empty:
        print(f"❌ Failed to retrieve quantitative data for {ticker}.")
        sys.exit(1)
        
    print(f"✅ Successfully downloaded {ticker} financials.")
    
    # 2. Test Agent & NVIDIA NIM Qualitative Stage
    print("\n--- [Step 2] Fetching Institutional Data & Running AI Diligence ---")
    agent = EquityScreenerAgent(min_mcap=0, max_mcap=999e12, deep_research=True)
    agent.universe = df
    
    sample_sector = df['sector'].iloc[0]
    print(f"Sector identified as: {sample_sector}")
    
    try:
        screener = agent._get_sector_screener(sample_sector)
    except Exception:
        from equity_screener_agent import BaseSectorScreener
        screener = BaseSectorScreener(df[df['sector'] == sample_sector], ai_service=agent.ai_service)

    screener.universe = df[df['sector'] == sample_sector].copy()
    screener.deep_research = True
    screener.defeatbeta_service = agent.defeatbeta_service
    
    # Run the funnel
    results = screener.run_sector_funnel()
    
    print("\n" + "="*80)
    print(f"🏆 FINAL ANALYSIS RESULTS FOR {ticker}")
    print("="*80)
    
    if not results.empty:
        row = results.iloc[0]
        
        # Display Quant Check
        print("\n📊 QUANTITATIVE METRICS:")
        print(f"  Price: ${row.get('price', 0):.2f}")
        print(f"  P/E Ratio: {row.get('pe_ratio', 'N/A')}")
        print(f"  Market Cap: ${row.get('market_cap', 0)/1e9:.2f}B")
        
        # Display Institutional Check
        print("\n🏛️ INSTITUTIONAL METRICS (DefeatBeta):")
        fv = row.get('fair_price')
        print(f"  Fair Value Estimate: ${f'{fv:.2f}' if fv and fv != 'None' else 'N/A (Calculated Fallback)'}")
        print(f"  Implied Upside: {row.get('dcf_upside', 0)*100:.1f}%")
        print(f"  Insider Activity Detected: {row.get('insider_buying', 'N/A')}")
        
        # Display AI Outputs
        print("\n🤖 AI QUALITATIVE REASONING (Nvidia NIM):")
        print(f"  Sentiment Score: {row.get('qual_sentiment', '0')}/100")
        print(f"  Sentiment Drift: {row.get('sentiment_drift', 'N/A')}")
        
        # New Evidence-Based Section
        is_sb = row.get('is_sandbagging')
        print(f"\n  [Sandbagging Check]: {'⚠️ DETECTED' if is_sb else 'None Detected'}")
        if is_sb:
            print(f"    Evidence: {row.get('sandbagging_evidence', 'No specific quote cited.')}")
            
        print("\n  [Key Highlights]:")
        print(f"    - Catalysts: {row.get('catalysts', 'N/A')}")
        print(f"    - Risk Flags: {row.get('risk_flags', 'N/A')}")
        
        print("\n  [Full AI Pipeline Analysis Summary]:")
        # Ensure we wrap text for the terminal
        import textwrap
        print(textwrap.indent(textwrap.fill(str(row.get('ai_summary', 'No summary generated.')), width=75), "    "))
        
    else:
        print(f"❌ {ticker} failed to pass the internal quantitative or AI filters.")
        
    print("\n" + "="*80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test a single ticker end-to-end')
    parser.add_argument('ticker', type=str, help='Ticker symbol (e.g., AAPL)')
    args = parser.parse_args()
    
    test_single_ticker(args.ticker.upper())
