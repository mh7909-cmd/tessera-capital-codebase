"""
Quick validation script.
Run: python3 test_run.py
"""
from financial_analyzer import FinancialAnalyzer
from sheets_processor import SheetsProcessor
import os
from dotenv import load_dotenv

load_dotenv()


def test_single_ticker():
    print("=" * 50)
    print("TEST 1: Single ticker analysis (AAPL)")
    print("=" * 50)
    analyzer = FinancialAnalyzer()
    result = analyzer.analyze_ticker("AAPL", "Apple Inc.", {})
    if result:
        print("PASS — Got analysis result:")
        for k, v in result.items():
            print(f"  {k:20s}: {str(v)[:100]}")
    else:
        print("FAIL — No data returned for AAPL")


def test_sheet_connection():
    print("\n" + "=" * 50)
    print("TEST 2: Google Sheets connection")
    print("=" * 50)
    try:
        processor = SheetsProcessor()
        data = processor.get_all_tickers_by_tab()
        if data:
            print(f"PASS — Connected. Found {len(data)} sector tab(s):")
            for tab, tickers in data.items():
                sample_cols = list(tickers[0].keys()) if tickers else []
                print(f"  Tab '{tab}': {len(tickers)} tickers | Columns: {sample_cols[:8]}...")
        else:
            print("WARN — Connected but no ticker tabs found")
    except Exception as e:
        print(f"FAIL — Sheet connection error: {e}")


def test_llm():
    print("\n" + "=" * 50)
    print("TEST 3: NVIDIA LLM synthesis")
    print("=" * 50)
    key = os.getenv("NVIDIA_API_KEY")
    if not key:
        print("SKIP — NVIDIA_API_KEY not set")
        return
    analyzer = FinancialAnalyzer()
    if not analyzer.llm:
        print("SKIP — LLM client not initialized")
        return
    thesis = analyzer.generate_llm_summary(
        ticker="MSFT",
        name="Microsoft Corporation",
        metrics={"rev_cagr": "15.2%", "roe": "38.5%", "f_score": 8, "z_score": "4.1",
                 "gross_margin": "69%", "net_margin": "35%", "fcf_margin": "30%", "debt_equity": "0.4"},
        source_row={"Overall Sentiment": "Bullish", "qual_score": "72.5"},
    )
    if thesis:
        print("PASS — LLM thesis generated:")
        print(f"  {thesis}")
    else:
        print("FAIL — Empty thesis returned")


if __name__ == "__main__":
    test_single_ticker()
    test_sheet_connection()
    test_llm()
    print("\nAll tests complete.")
