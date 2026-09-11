"""
Ad-Hoc Deep Research Tool: Full-Context AI Research
Performs high-resolution, single-ticker diligence on any stock.
Usage: python deep_research.py --ticker <SYMBOL>
"""

import argparse
import sys
import os
import re
import json
from datetime import datetime
from data_ingestion import YFinanceProvider, DefeatBetaProvider
from nlp_analysis import AIService

def run_single_ticker_research(ticker_symbol: str):
    print("\n" + "="*80)
    print(f"AD-HOC INSTITUTIONAL RESEARCH: {ticker_symbol}")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Initialize Providers
    yf_provider = YFinanceProvider()
    db_provider = DefeatBetaProvider()
    ai_service = AIService()
    
    # 2. Fetch Basic Data
    print(f"\n[1/3] Fetching core metrics for {ticker_symbol}...")
    basic_info = yf_provider.get_ticker_info(ticker_symbol)
    if not basic_info or basic_info.get('market_cap', 0) == 0:
        print(f"CRITICAL ERROR: Could not find data for ticker '{ticker_symbol}'.")
        return

    company_name = basic_info.get('company_name', ticker_symbol)
    sector = basic_info.get('sector', 'Unknown')
    
    print(f"  Company: {company_name}")
    print(f"  Sector: {sector}")
    print(f"  Market Cap: ${basic_info.get('market_cap', 0)/1e9:.2f}B")
    
    # 3. Fetch Deep Institutional Data (Transcripts)
    print(f"\n[2/3] Downloading latest earnings transcripts (FULL CONTEXT)...")
    research_data = db_provider.get_deep_research(ticker_symbol)
    transcripts = research_data.get('transcripts', [])
    insider_buying = research_data.get('insider_buying', False)
    
    if not transcripts:
        print("  [WARN] No transcripts found. AI will perform analysis on basic metadata.")
    else:
        print(f"  ✓ {len(transcripts)} transcripts loaded successfully.")

    # 4. Run AI "Beast Mode" Analysis
    print(f"\n[3/3] Initiating Full-Context AI Qualitative Diligence...")
    ai_report = ai_service.analyze_equity_qualitative(
        ticker_symbol, company_name, sector, 
        transcripts=transcripts,
        insider_buying=insider_buying
    )
    
    # 5. Generate Terminal Report
    print("\n" + "="*80)
    print(f"INSTITUTIONAL RESEARCH NOTE: {ticker_symbol}")
    print("="*80)
    
    print(f"\nOVERALL SENTIMENT: {ai_report.get('overall_sentiment', 0)}/100")
    print(f"SENTIMENT DRIFT:  {ai_report.get('sentiment_drift', 'Stable').upper()}")
    print(f"CONFIDENCE SCORE: {ai_report.get('confidence_score', 0)}/100")
    
    print(f"\nSUMMARY:\n{ai_report.get('summary', 'No summary generated.')}")
    
    if ai_report.get('is_sandbagging'):
        print("\n[!] ALERT: Management may be SANDBAGGING guidance.")
    
    if ai_report.get('catalysts'):
        print("\nTOP CATALYSTS:")
        for cat in ai_report.get('catalysts', []):
            print(f"  • {cat}")
            
    if ai_report.get('risk_flags'):
        print("\nHIDDEN QUALITATIVE RISKS:")
        for risk in ai_report.get('risk_flags', []):
            print(f"  ⚠ {risk}")

    # Financial Pulse Check (Institutional)
    print("\nFUNDAMENTAL PULSE CHECK:")
    fair_price = research_data.get('fair_price')
    upside = research_data.get('upside')
    wacc = research_data.get('wacc')
    roic = research_data.get('roic')

    print(f"  DCF Fair Value: {f'${fair_price:.2f}' if fair_price is not None else 'N/A'}")
    print(f"  Implied Upside: {f'{upside*100:.1f}%' if upside is not None else 'N/A'}")
    print(f"  WACC:           {f'{wacc*100:.1f}%' if wacc is not None else 'N/A'}")
    print(f"  ROIC:           {f'{roic*100:.1f}%' if roic is not None else 'N/A'}")
    
    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deep Research Single Ticker")
    parser.add_argument("--ticker", type=str, required=True, help="Ticker symbol (e.g. JPM, AAPL)")
    args = parser.parse_args()
    
    try:
        run_single_ticker_research(args.ticker.upper())
    except KeyboardInterrupt:
        print("\nResearch cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        sys.exit(1)
