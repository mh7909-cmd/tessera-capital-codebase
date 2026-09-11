"""
Financial Modeling Prep (FMP) Data Provider
High-quality fundamental data with smart caching and earnings calendar tracking.
"""

import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os


class FMPProvider:
    """
    Financial Modeling Prep API integration.
    Provides professional-grade fundamental data.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.rate_limit_delay = 0.3  # 3 calls per second (free tier)
        
    def get_stock_fundamentals(self, ticker: str) -> Dict:
        """
        Fetch comprehensive fundamentals for a single stock.
        Returns all metrics needed for screening.
        """
        if ticker.upper() == "FLY":
            return None

        try:
            # Get company profile (sector, market cap, etc.)
            profile = self._get_profile(ticker)
            
            # Get key metrics (margins, ratios, etc.)
            metrics = self._get_key_metrics(ticker)
            
            # Get financial ratios
            ratios = self._get_financial_ratios(ticker)
            
            # Combine into single record
            fundamentals = {
                'ticker': ticker,
                'company_name': profile.get('companyName', ''),
                'sector': profile.get('sector', ''),
                'industry': profile.get('industry', ''),
                'market_cap': profile.get('mktCap', 0),
                'price': profile.get('price', 0),
                'beta': profile.get('beta', 0),
                'currency': profile.get('currency', 'USD'),
                
                # Valuation metrics
                'pe_ratio': ratios.get('priceEarningsRatio', None),
                'price_to_book': ratios.get('priceToBookRatio', None),
                'ev_to_sales': ratios.get('enterpriseValueMultiple', None),
                'ev_to_ebitda': ratios.get('evToEbitda', None),
                
                # Profitability metrics
                'gross_margin': metrics.get('grossProfitMargin', None),
                'operating_margin': metrics.get('operatingProfitMargin', None),
                'net_margin': metrics.get('netProfitMargin', None),
                'roe': ratios.get('returnOnEquity', None),
                'roa': ratios.get('returnOnAssets', None),
                'roic': metrics.get('roic', None),
                
                # Growth metrics
                'revenue_growth': metrics.get('revenuePerShareGrowth', None),
                'earnings_growth': metrics.get('netIncomePerShareGrowth', None),
                
                # Balance sheet metrics
                'debt_to_equity': ratios.get('debtEquityRatio', None),
                'current_ratio': ratios.get('currentRatio', None),
                'quick_ratio': ratios.get('quickRatio', None),
                
                # Cash flow metrics
                'fcf': metrics.get('freeCashFlowPerShare', None),
                'operating_cash_flow': metrics.get('operatingCashFlowPerShare', None),
                
                # Timestamp
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            time.sleep(self.rate_limit_delay)  # Rate limiting
            return fundamentals
            
        except Exception as e:
            if ticker.upper() != "FLY":
                print(f"Error fetching {ticker}: {e}")
            return None
    
    def _get_profile(self, ticker: str) -> Dict:
        """Get company profile."""
        url = f"{self.base_url}/profile/{ticker}?apikey={self.api_key}"
        response = requests.get(url)
        data = response.json()
        return data[0] if data else {}
    
    def _get_key_metrics(self, ticker: str) -> Dict:
        """Get key financial metrics."""
        url = f"{self.base_url}/key-metrics-ttm/{ticker}?apikey={self.api_key}"
        response = requests.get(url)
        data = response.json()
        return data[0] if data else {}
    
    def _get_financial_ratios(self, ticker: str) -> Dict:
        """Get financial ratios."""
        url = f"{self.base_url}/ratios-ttm/{ticker}?apikey={self.api_key}"
        response = requests.get(url)
        data = response.json()
        return data[0] if data else {}
    
    def get_sp500_list(self) -> List[str]:
            """Get S&P 500 tickers from Wikipedia, then use FMP for fundamentals."""
            import pandas as pd
        
            print("  Fetching S&P 500 list from Wikipedia...")
        
            try:
                # Wikipedia has the current S&P 500 list (free, always updated)
                url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                tables = pd.read_html(url)
                sp500_table = tables[0]
            
                # Get tickers and clean them
                tickers = sp500_table['Symbol'].tolist()
                # Replace periods with hyphens for Yahoo/FMP compatibility
                clean_tickers = [t.replace('.', '-') for t in tickers]
            
                print(f"  Found {len(clean_tickers)} S&P 500 tickers")
                return clean_tickers
            
            except Exception as e:
                print(f"  Error fetching from Wikipedia: {e}")
                # Fallback: hardcoded list of major stocks
                print("  Using fallback list of major US stocks...")
                return [
                    # Tech
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AVGO', 'ORCL', 'ADBE',
                    'CRM', 'CSCO', 'ACN', 'AMD', 'INTC', 'IBM', 'QCOM', 'TXN', 'INTU', 'NOW',
                    # Finance
                    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SPGI', 'CME', 'SCHW',
                    'AXP', 'USB', 'PNC', 'TFC', 'COF', 'BK', 'STT', 'NTRS', 'FRC', 'CFG',
                    # Healthcare
                    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY',
                    'AMGN', 'CVS', 'GILD', 'CI', 'REGN', 'ISRG', 'VRTX', 'HCA', 'BIIB', 'ZTS',
                    # Consumer
                    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'BKNG', 'CMG',
                    # And more... (this is just a sample)
                ]
        
    def get_nasdaq100_list(self) -> List[str]:
        """Get NASDAQ 100 constituent tickers."""
        url = f"{self.base_url}/nasdaq_constituent?apikey={self.api_key}"
        response = requests.get(url)
        data = response.json()
        return [item['symbol'] for item in data]
    
    def get_dow_jones_list(self) -> List[str]:
        """Get Dow Jones constituent tickers."""
        url = f"{self.base_url}/dowjones_constituent?apikey={self.api_key}"
        response = requests.get(url)
        data = response.json()
        return [item['symbol'] for item in data]


class EarningsCalendar:
    """
    Track earnings reports and trigger data refreshes.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
    
    def get_reporting_today(self) -> List[str]:
        """Get tickers reporting earnings today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_reporting_on_date(today)
    
    def get_reporting_on_date(self, date: str) -> List[str]:
        """Get tickers reporting on specific date (YYYY-MM-DD)."""
        url = f"{self.base_url}/earning_calendar?from={date}&to={date}&apikey={self.api_key}"
        
        try:
            response = requests.get(url)
            data = response.json()
            return [item['symbol'] for item in data if 'symbol' in item]
        except:
            return []
    
    def get_reporting_this_week(self) -> List[str]:
        """Get tickers reporting this week."""
        today = datetime.now()
        week_end = today + timedelta(days=7)
        
        from_date = today.strftime("%Y-%m-%d")
        to_date = week_end.strftime("%Y-%m-%d")
        
        url = f"{self.base_url}/earning_calendar?from={from_date}&to={to_date}&apikey={self.api_key}"
        
        try:
            response = requests.get(url)
            data = response.json()
            return [item['symbol'] for item in data if 'symbol' in item]
        except:
            return []


class DataCache:
    """
    Smart caching system for fundamental data.
    Minimizes API calls by storing data locally.
    """
    
    def __init__(self, cache_file: str = 'universe_cache.csv'):
        self.cache_file = cache_file
        
        # Load existing cache or create new
        if os.path.exists(cache_file):
            self.data = pd.read_csv(cache_file)
            print(f"Loaded cache: {len(self.data)} stocks")
        else:
            self.data = pd.DataFrame()
            print("Created new cache")
    
    def get(self, ticker: str) -> Optional[Dict]:
        """Get cached data for ticker."""
        if ticker not in self.data['ticker'].values:
            return None
        
        row = self.data[self.data['ticker'] == ticker].iloc[0]
        return row.to_dict()
    
    def get_age_days(self, ticker: str) -> int:
        """How old is cached data for this ticker (in days)?"""
        if ticker not in self.data['ticker'].values:
            return 999  # Not in cache
        
        row = self.data[self.data['ticker'] == ticker].iloc[0]
        last_updated = pd.to_datetime(row['last_updated'])
        days_old = (datetime.now() - last_updated).days
        
        return days_old
    
    def needs_refresh(self, ticker: str, max_age_days: int = 90) -> bool:
        """Should we refresh this ticker?"""
        age = self.get_age_days(ticker)
        return age >= max_age_days
    
    def update(self, ticker: str, fundamentals: Dict):
        """Update cache with fresh data."""
        if fundamentals is None:
            return
        
        # Remove old entry if exists
        self.data = self.data[self.data['ticker'] != ticker]
        
        # Add new entry
        new_row = pd.DataFrame([fundamentals])
        self.data = pd.concat([self.data, new_row], ignore_index=True)
    
    def save(self):
        """Save cache to disk."""
        self.data.to_csv(self.cache_file, index=False)
        print(f"✓ Cache saved: {len(self.data)} stocks")
    
    def get_all(self) -> pd.DataFrame:
        """Get all cached data."""
        return self.data.copy()
    
    def get_stale_tickers(self, max_age_days: int = 90) -> List[str]:
        """Get list of tickers with stale data."""
        if len(self.data) == 0:
            return []
        
        stale = []
        for ticker in self.data['ticker']:
            if self.needs_refresh(ticker, max_age_days):
                stale.append(ticker)
        
        return stale


class SmartDataManager:
    """
    Orchestrates FMP data provider, earnings calendar, and cache.
    Implements intelligent refresh strategy.
    """
    
    def __init__(self, api_key: str, cache_file: str = 'universe_cache.csv'):
        self.fmp = FMPProvider(api_key)
        self.calendar = EarningsCalendar(api_key)
        self.cache = DataCache(cache_file)
        self.api_key = api_key
    
    def build_initial_universe(self, ticker_list: List[str], batch_size: int = 250):
        """
        Download fundamentals for full universe.
        Respects rate limits by batching.
        """
        total = len(ticker_list)
        print(f"\nBuilding universe: {total} stocks")
        print(f"Batch size: {batch_size} stocks/day")
        print(f"Estimated time: {total/batch_size:.1f} days")
        print("="*60)
        
        downloaded = 0
        failed = 0
        
        for i, ticker in enumerate(ticker_list, 1):
            # Check if already in cache
            if ticker in self.cache.data.get('ticker', pd.Series()).values:
                age = self.cache.get_age_days(ticker)
                if age < 90:
                    print(f"  [{i}/{total}] {ticker} - cached ({age}d old)")
                    continue
            
            # Download fundamentals
            print(f"  [{i}/{total}] {ticker} - downloading...", end=' ')
            fundamentals = self.fmp.get_stock_fundamentals(ticker)
            
            if fundamentals:
                self.cache.update(ticker, fundamentals)
                downloaded += 1
                print("✓")
            else:
                failed += 1
                print("✗")
            
            # Save cache every 50 stocks
            if i % 50 == 0:
                self.cache.save()
            
            # Respect daily limit
            if downloaded >= batch_size:
                print(f"\n⚠ Reached daily limit ({batch_size} stocks)")
                print(f"Progress: {i}/{total} ({i/total*100:.1f}%)")
                print(f"Resume tomorrow to continue")
                break
        
        # Final save
        self.cache.save()
        
        print("\n" + "="*60)
        print(f"✓ Downloaded: {downloaded} stocks")
        print(f"✗ Failed: {failed} stocks")
        print(f"Total in cache: {len(self.cache.data)} stocks")
        
        return self.cache.get_all()
    
    def daily_refresh(self, also_refresh_stale: bool = True):
        """
        Daily automated refresh.
        Updates stocks that reported earnings + stale data.
        """
        print("\n" + "="*60)
        print("DAILY DATA REFRESH")
        print("="*60)
        
        # Get stocks reporting today
        print("\nChecking earnings calendar...")
        reporting = self.calendar.get_reporting_today()
        print(f"  Stocks reporting today: {len(reporting)}")
        
        # Get stale stocks
        stale = []
        if also_refresh_stale:
            stale = self.cache.get_stale_tickers(max_age_days=90)
            print(f"  Stocks with stale data (>90d): {len(stale)}")
        
        # Combine (remove duplicates)
        to_refresh = list(set(reporting + stale))
        print(f"  Total to refresh: {len(to_refresh)}")
        
        if len(to_refresh) == 0:
            print("\n✓ No refresh needed. All data is current.")
            return
        
        # Refresh
        print(f"\nRefreshing {len(to_refresh)} stocks...")
        success = 0
        failed = 0
        
        for ticker in to_refresh:
            print(f"  {ticker}...", end=' ')
            fundamentals = self.fmp.get_stock_fundamentals(ticker)
            
            if fundamentals:
                self.cache.update(ticker, fundamentals)
                success += 1
                print("✓")
            else:
                failed += 1
                print("✗")
        
        # Save
        self.cache.save()
        
        print("\n" + "="*60)
        print(f"✓ Refreshed: {success} stocks")
        print(f"✗ Failed: {failed} stocks")
        print(f"API calls used: ~{1 + len(to_refresh)}")
        print("="*60)
    
    def get_screener_universe(self, min_mcap: float = 1e9, max_mcap: float = 50e9) -> pd.DataFrame:
        """
        Get universe for screening with market cap filter.
        Uses cached data (no API calls).
        """
        df = self.cache.get_all()
        
        if len(df) == 0:
            print("⚠ Cache is empty. Run build_initial_universe() first.")
            return df
        
        # Apply market cap filter
        filtered = df[
            (df['market_cap'] >= min_mcap) &
            (df['market_cap'] <= max_mcap)
        ].copy()
        
        print(f"\nScreener universe: {len(filtered)} stocks")
        print(f"  Market cap: ${min_mcap/1e9:.1f}B - ${max_mcap/1e9:.1f}B")
        print(f"  Sectors: {filtered['sector'].nunique()}")
        
        return filtered


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize with your API key
    API_KEY = "YOUR_FMP_API_KEY_HERE"
    
    manager = SmartDataManager(API_KEY)
    
    # Example 1: Build initial universe (S&P 500)
    print("Example 1: Building S&P 500 universe")
    sp500_tickers = manager.fmp.get_sp500_list()
    print(f"S&P 500 tickers: {len(sp500_tickers)}")
    
    # Download (respects 250/day limit)
    # manager.build_initial_universe(sp500_tickers, batch_size=250)
    
    # Example 2: Daily refresh
    # manager.daily_refresh()
    
    # Example 3: Get screener universe
    # universe = manager.get_screener_universe(min_mcap=1e9, max_mcap=50e9)
    # print(universe.head())
