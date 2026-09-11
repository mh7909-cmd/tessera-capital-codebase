from defeatbeta_api.data.ticker import Ticker
import sys

def debug_ticker(symbol):
    print(f"Debugging {symbol}...")
    try:
        ticker = Ticker(symbol)
        is_stmt = ticker.annual_income_statement()
        print(f"Income Statement empty: {is_stmt.is_empty()}")
        if not is_stmt.is_empty():
            print(is_stmt.df().head())
        else:
            print("No data in income statement.")
            
        bs_stmt = ticker.annual_balance_sheet()
        print(f"Balance Sheet empty: {bs_stmt.is_empty()}")
        
        cf_stmt = ticker.annual_cash_flow()
        print(f"Cash Flow empty: {cf_stmt.is_empty()}")
        
    except Exception as e:
        print(f"Caught exception: {e}")

if __name__ == "__main__":
    debug_ticker("AAPL")
