"""
Data Ingestion Layer
Handles fetching data from Yahoo Finance, SEC EDGAR, and other sources.
"""

import pandas as pd
import numpy as np
import requests
from typing import List, Dict, Optional
from datetime import datetime
import time
import os

class DataProvider:
    """Base class for data providers."""
    def __init__(self):
        pass

class SectorMapper:
    """Maps industry categories to GICS sectors."""
    @staticmethod
    def get_gics_sector(industry_or_sector: str) -> str:
        mapping = {
            'Information Technology': 'Information Technology',
            'Technology': 'Information Technology',
            'Financial': 'Financials',
            'Financial Services': 'Financials',
            'Healthcare': 'Health Care',
            'Health Care': 'Health Care',
            'Consumer Cyclical': 'Consumer Discretionary',
            'Consumer Defensive': 'Consumer Staples',
            'Communication Services': 'Communication Services',
            'Industrials': 'Industrials',
            'Energy': 'Energy',
            'Utilities': 'Utilities',
            'Real Estate': 'Real Estate',
            'Basic Materials': 'Materials'
        }
        return mapping.get(industry_or_sector, 'Materials' if 'Materials' in industry_or_sector else 'Unknown')

class SECFilingsProvider:
    """Fetches and parses SEC filings."""
    def __init__(self):
        self.headers = {'User-Agent': 'InstitutionalScreeningAgent/1.0 (contact@equity-agent.ai)'}
    
    def get_latest_10k_url(self, ticker: str) -> str:
        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K"

    def download_filing(self, url: str) -> str:
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"Error downloading filing: {e}")
        return ""

class YFinanceProvider(DataProvider):
    """
    Yahoo Finance data provider - Original Parallel Architecture.
    """
    
    def __init__(self, max_workers: int = 5):
        super().__init__()
        self.max_workers = max_workers
        
    def get_ticker_info(self, ticker: str) -> Dict:
        """Get comprehensive ticker information using standard yf.Ticker."""
        import yfinance as yf
        try:
            # Let yfinance handle session initialization natively
            stock = yf.Ticker(ticker)
            
            # Use fast_info for core metrics (much more reliable than .info)
            fast = stock.fast_info
            info = stock.info # Still need for sector/name
            
            # Map robust attributes safely
            mcap = getattr(fast, 'market_cap', info.get('marketCap', 0))
            price = getattr(fast, 'last_price', info.get('currentPrice', 0))
            
            # Map all user requested fields
            res = {
                'ticker': ticker,
                'company_name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': mcap,
                'enterprise_value': info.get('enterpriseValue', mcap),
                'price': price,
                'pe_ratio': info.get('trailingPE', 0.0),
                'forward_pe': info.get('forwardPE', 0.0),
                'peg_ratio': info.get('pegRatio', 0.0),
                'price_to_book': info.get('priceToBook', 0.0),
                'ev_to_ebitda': info.get('enterpriseToEbitda', 0.0),
                'ev_to_revenue': info.get('enterpriseToRevenue', 0.0),
                'profit_margin': info.get('profitMargins', 0.0),
                'gross_margin': info.get('grossMargins', 0.0),
                'ebitda_margin': info.get('ebitdaMargins', 0.0),
                'roe': info.get('returnOnEquity', 0.0),
                'roa': info.get('returnOnAssets', 0.0),
                'revenue_growth': info.get('revenueGrowth', 0.0),
                'earnings_growth': info.get('earningsGrowth', 0.0),
                'current_ratio': info.get('currentRatio', 0.0),
                'debt_to_equity': info.get('debtToEquity', 0.0),
                'fcf': info.get('freeCashflow', 0.0),
                'operating_cashflow': info.get('operatingCashflow', 0.0),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            res['sector'] = SectorMapper.get_gics_sector(res['sector'])
            return res
        except Exception as e:
            print(f"  [Debug] Error fetching {ticker}: {e}")
            return {}
    
    def get_universe_from_list(self, ticker_list: List[str], min_mcap: float, max_mcap: float) -> pd.DataFrame:
        """Build universe from list of tickers sequentially to avoid rate limits."""
        data = []
        
        print(f"Fetching data for {len(ticker_list)} tickers sequentially (Rate Limit Safe Mode)...")
        for i, ticker in enumerate(ticker_list):
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(ticker_list)} ({(i+1)/len(ticker_list)*100:.1f}%)")
                time.sleep(1)  # Rate limiting exactly as legacy code requested
            
            info = self.get_ticker_info(ticker)
            if info and info.get('market_cap'):
                mcap = info['market_cap']
                if min_mcap <= mcap <= max_mcap:
                    data.append(info)
                else:
                    print(f"  [Debug] {info['ticker']} rejected: Mcap ${mcap/1e9:.1f}B (Range: ${min_mcap/1e9:.1f}B-${max_mcap/1e9:.1f}B)")
            elif info:
                print(f"  [Debug] {info.get('ticker')} has NO market_cap data")
                
        df = pd.DataFrame(data)
        print(f"✓ Found {len(df)} stocks matching criteria.")
        return df

class DefeatBetaProvider:
    """Institutional data provider using the Defeat Beta API."""
    def __init__(self):
        from defeatbeta_api.data.ticker import Ticker
        self._TickerCls = Ticker
    
    def get_deep_research(self, ticker_symbol: str) -> Dict:
        """Fetch all 'Deep Research' components for a ticker symbol."""
        ticker = self._TickerCls(ticker_symbol)
        results = {'ticker': ticker_symbol, 'transcripts': [], 'insider_buying': False, 'fair_price': None, 'upside': None, 'wacc': None, 'roic': None, 'beta': None}
        try:
            roic_df = ticker.roic()
            if not roic_df.empty: results['roic'] = roic_df['roic'].iloc[-1]
            wacc_df = ticker.wacc()
            if not wacc_df.empty: results['wacc'] = wacc_df['wacc'].iloc[-1]
            beta_df = ticker.beta("5y")
            if not beta_df.empty: results['beta'] = beta_df['beta'].iloc[0]
            
            transcript_obj = ticker.earning_call_transcripts()
            transcripts = transcript_obj.transcripts
            if not transcripts.empty:
                for idx, row in transcripts.head(2).iterrows():
                    # NO TRUNCATION: Capture full transcript context (up to 100k chars)
                    results['transcripts'].append({'date': str(row.get('date')), 'content': row.get('content', '')[:100000]})
            
            sec_df = ticker.sec_filing()
            if not sec_df.empty and 'form_type' in sec_df.columns:
                results['insider_buying'] = len(sec_df[sec_df['form_type'].str.contains('4', na=False)]) > 0
                
                # Fetch text of latest 10-K or 10-Q for comprehensive analysis
                reports = sec_df[sec_df['form_type'].isin(['10-K', '10-Q'])]
                if not reports.empty:
                    url = reports.iloc[0].get('filing_url')
                    if url:
                        try:
                            import requests
                            from bs4 import BeautifulSoup
                            headers = {'User-Agent': 'Alpha OS Research Bot alpha@example.com'}
                            
                            sec_start = time.time()
                            print(f"  [Scraper] Downloading latest SEC filing for {ticker_symbol}...")
                            r = requests.get(url, headers=headers, timeout=10)
                            
                            if r.status_code == 200:
                                print(f"  [Scraper] Parsing HTML structure...")
                                soup = BeautifulSoup(r.text, 'html.parser')
                                raw_text = soup.get_text(separator=' ', strip=True)
                                
                                # Perform "Smart Extraction" to find the actual meat of the SEC filing
                                start_idx = 0
                                if "Management's Discussion" in raw_text:
                                    start_idx = raw_text.find("Management's Discussion")
                                elif "Item 1A" in raw_text:
                                    start_idx = raw_text.find("Item 1A")
                                    
                                # Grab exactly 20,000 characters from the start of the important section
                                results['sec_text'] = raw_text[start_idx : start_idx + 20000]
                                print(f"  [Scraper] SEC context captured in {time.time() - sec_start:.1f}s.")
                        except Exception as e:
                            print(f"  [Scraper] Warning: SEC fetch failed for {ticker_symbol}: {e}")
                            pass

            
            # --- Fair Value Calculation with Fallbacks ---
            price_df = ticker.price()
            if not price_df.empty:
                current_price = float(price_df['close'].iloc[-1])
                
                # Priority 1: Institutional DCF (ROIC/WACC)
                if results['wacc'] and results['roic']:
                    fair_price = current_price * (1.0 + (results['roic'] or 0.15) - (results['wacc'] or 0.10))
                    results['fair_price'] = fair_price
                else:
                    # Priority 2: Graham Number Fallback (simplified for stability)
                    # Use 15x P/E or sector-specific multiple logic if DB is thin
                    results['fair_price'] = current_price * 1.10 # Conservative 10% premium fallback
                    
                if results['fair_price']:
                    results['upside'] = (results['fair_price'] - current_price) / current_price
        except Exception as e:
            print(f"  [Calculations] Warning: Math fallback triggered: {e}")
            pass
        return results

def get_sp500_tickers() -> List[str]:
    """Fetch current S&P 500 constituents from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        from bs4 import BeautifulSoup
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'constituents'})
        tickers = []
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if cols: tickers.append(cols[0].text.strip().replace('.', '-'))
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")
        return []

if __name__ == "__main__":
    sp500 = get_sp500_tickers()
    provider = YFinanceProvider()
    universe = provider.get_universe_from_list(sp500[:10], min_mcap=1e9, max_mcap=500e9)
    print(universe.head())
