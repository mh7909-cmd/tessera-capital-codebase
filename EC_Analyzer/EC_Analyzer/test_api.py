from defeatbeta_api.data.ticker import Ticker
import pandas as pd

def test_fetch_transcripts(ticker_symbol):
    print(f"--- Testing {ticker_symbol} ---")
    ticker = Ticker(ticker_symbol)
    transcripts_obj = ticker.earning_call_transcripts()
    
    # Get list of transcripts
    df_list = transcripts_obj.get_transcripts_list()
    if df_list.empty:
        print("No transcripts found.")
        return
    
    # Sort by report_date descending
    df_list = df_list.sort_values(by='report_date', ascending=False)
    print(f"Found {len(df_list)} transcripts.")
    
    # Pick top 2 for testing
    top_n = df_list.head(2)
    for idx, row in top_n.iterrows():
        year = row['fiscal_year']
        quarter = row['fiscal_quarter']
        date = row['report_date']
        print(f"Fetching FY{year} Q{quarter} (Reported: {date})...")
        
        try:
            df_paragraphs = transcripts_obj.get_transcript(year, quarter)
            full_text = " ".join(df_paragraphs['content'].astype(str).tolist())
            print(f"  Snippet: {full_text[:200]}...")
            print(f"  Total length: {len(full_text)} chars")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    test_fetch_transcripts("TSLA")
