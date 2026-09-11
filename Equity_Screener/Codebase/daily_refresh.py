"""
Daily Refresh Script
Run this each morning to update stocks that reported earnings.
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

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*80)
    print("DAILY DATA REFRESH - FMP Provider")
    print("="*80)
    
    # Initialize manager
    manager = SmartDataManager(API_KEY, cache_file=CACHE_FILE)
    
    # Run daily refresh
    # - Checks earnings calendar for today's reporters
    # - Refreshes stocks with stale data (>90 days)
    # - Updates cache
    manager.daily_refresh(also_refresh_stale=True)
    
    print("\n✓ Daily refresh complete!")
    print("You can now run the screener with fresh data.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
