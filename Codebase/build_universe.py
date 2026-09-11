"""
Initial Universe Builder
Run this ONCE to download the full S&P 500 dataset.
Takes 2 days (250 stocks/day on free tier).
"""

import sys
from fmp_provider import SmartDataManager

# =============================================================================
# CONFIGURATION
# =============================================================================

# Your FMP API key
API_KEY = "tW3H8UXqZxm87wyt4YeJ1jJI4XPnNf4y"  # Replace with your actual key

# Cache file location
CACHE_FILE = "universe_cache.csv"

# Daily download limit (free tier = 250)
BATCH_SIZE = 250

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*80)
    print("INITIAL UNIVERSE BUILDER - FMP Provider")
    print("="*80)
    
    # Initialize manager
    manager = SmartDataManager(API_KEY, cache_file=CACHE_FILE)
    
    # Get S&P 500 ticker list
    print("\nFetching S&P 500 constituent list...")
    sp500_tickers = manager.fmp.get_sp500_list()
    print(f"✓ Found {len(sp500_tickers)} S&P 500 stocks")
    
    # Build universe
    print(f"\nDownloading fundamentals...")
    print(f"Note: Free tier limit = {BATCH_SIZE} stocks/day")
    print(f"Total stocks: {len(sp500_tickers)}")
    print(f"Days needed: {len(sp500_tickers)/BATCH_SIZE:.1f}")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return 1
    
    # Download
    universe = manager.build_initial_universe(
        ticker_list=sp500_tickers,
        batch_size=BATCH_SIZE
    )
    
    print("\n" + "="*80)
    print("UNIVERSE BUILD SUMMARY")
    print("="*80)
    print(f"Total stocks in cache: {len(universe)}")
    print(f"Sectors represented: {universe['sector'].nunique()}")
    print()
    print("Next steps:")
    print("  1. If not complete, run this script again tomorrow")
    print("  2. Once complete, run: python run_screener.py --data-source fmp")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
