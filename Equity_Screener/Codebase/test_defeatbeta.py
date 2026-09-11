from defeatbeta_api.data.ticker import Ticker
import pandas as pd
import json

def test_defeatbeta_api():
    print("🚀 Testing Defeat Beta API...")
    ticker_symbol = "MSFT"
    ticker = Ticker(ticker_symbol)
    
    print(f"\n--- Testing Information for {ticker_symbol} ---")
    try:
        info = ticker.info()
        print(f"Name: {info.get('longName')}")
        print(f"Sector: {info.get('sector')}")
        print(f"Market Cap: {info.get('marketCap')}")
    except Exception as e:
        print(f"Error fetching info: {e}")

    print(f"\n--- Testing Transcripts ---")
    try:
        transcripts = ticker.earning_call_transcripts()
        if not transcripts.empty:
            print(f"Found {len(transcripts)} transcripts.")
            print(f"Snippet from latest: {transcripts.iloc[0]['content'][:100]}...")
        else:
            print("No transcripts found.")
    except Exception as e:
        print(f"Error fetching transcripts: {e}")

    print(f"\n--- Testing Insider Trading ---")
    try:
        # Based on research, insider trading might be in a different method or via SEC filings
        sec_filings = ticker.sec_filings()
        if not sec_filings.empty:
            print(f"Found {len(sec_filings)} SEC filings.")
            print(f"Recent filings:\n{sec_filings.head(2)}")
        else:
            print("No SEC filings found.")
    except Exception as e:
        print(f"Error fetching SEC filings: {e}")

if __name__ == "__main__":
    test_defeatbeta_api()
