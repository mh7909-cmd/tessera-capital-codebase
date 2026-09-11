"""
AI-Native Fundamental Equity Screening Agent
Funnels entire US equity universe ($1B-$50B market cap) through sector-specific filters
to identify 10 highest-conviction names per sector for deep diligence.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings('ignore')

from nlp_analysis import AIService

# GICS Sector Definitions
GICS_SECTORS = [
    "Information Technology",
    "Financials", 
    "Health Care",
    "Consumer Discretionary",
    "Communication Services",
    "Industrials",
    "Consumer Staples",
    "Energy",
    "Utilities",
    "Real Estate",
    "Materials"
]


class EquityScreenerAgent:
    """
    Main orchestrator for sector-by-sector fundamental screening.
    """
    
    def __init__(self, min_mcap: float = 1e9, max_mcap: float = 50e9, 
                 api_key: Optional[str] = None, deep_research: bool = False):
        from data_ingestion import DefeatBetaProvider
        self.min_mcap = min_mcap
        self.max_mcap = max_mcap
        self.universe = None
        self.sector_results = {}
        self.ai_service = AIService(api_key=api_key)
        self.defeatbeta_service = DefeatBetaProvider()
        self.deep_research = deep_research
        
    def load_universe(self, universe_file: str = None) -> pd.DataFrame:
        """Load US equity universe with market cap filter."""
        print("Loading US equity universe...")
        if universe_file:
            self.universe = pd.read_csv(universe_file)
        else:
            self.universe = pd.DataFrame(columns=[
                'ticker', 'company_name', 'sector', 'market_cap',
                'price', 'shares_outstanding'
            ])
        return self.universe
    
    def run_full_screen(self, sectors: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Execute screening process across sectors.
        If sectors is provided, only screen those sectors.
        """
        print("\n" + "="*80)
        print("STARTING AI-NATIVE FUNDAMENTAL EQUITY SCREEN")
        print("="*80)
        
        # Mandatory: Filter universe to only include official GICS sectors
        original_count = len(self.universe)
        self.universe = self.universe[self.universe['sector'].isin(GICS_SECTORS)]
        filtered_count = len(self.universe)
        
        if original_count > filtered_count:
            print(f"  [Portfolio Manager] Filtered out {original_count - filtered_count} stocks with non-standard sector mappings.")
        
        active_sectors = sectors if sectors else GICS_SECTORS
        
        for sector in active_sectors:
            if sector not in GICS_SECTORS:
                print(f"  [WARN] Skipping unknown sector: {sector}")
                continue
                
            print(f"\n{'='*80}")
            print(f"SECTOR: {sector}")
            print(f"{'='*80}")
            
            screener = self._get_sector_screener(sector)
            try:
                top_10 = screener.run_sector_funnel()
                self.sector_results[sector] = top_10
            except Exception as e:
                print(f"✗ Error during {sector} screen: {e}")
                self.sector_results[sector] = pd.DataFrame()
            
            print(f"\n✓ {sector}: Identified {len(self.sector_results[sector])} stocks for deep diligence")
        
        return self.sector_results
    
    def _get_sector_screener(self, sector: str):
        sector_map = {
            "Information Technology": ITSectorScreener,
            "Financials": FinancialsSectorScreener,
            "Health Care": HealthCareSectorScreener,
            "Consumer Discretionary": ConsumerDiscSectorScreener,
            "Communication Services": CommServicesSectorScreener,
            "Industrials": IndustrialsSectorScreener,
            "Consumer Staples": ConsumerStaplesSectorScreener,
            "Energy": EnergySectorScreener,
            "Utilities": UtilitiesSectorScreener,
            "Real Estate": RealEstateSectorScreener,
            "Materials": MaterialsSectorScreener
        }
        
        screener_class = sector_map.get(sector)
        if screener_class:
            sector_universe = self.universe[self.universe['sector'] == sector].copy()
            screener = screener_class(sector_universe, ai_service=self.ai_service)
            screener.defeatbeta_service = self.defeatbeta_service
            screener.deep_research = self.deep_research
            return screener
        else:
            raise ValueError(f"Unknown sector: {sector}")
    
    def export_results(self, output_dir: str = "./"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}equity_screen_results_{timestamp}.xlsx"
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            summary_data = []
            for sector, df in self.sector_results.items():
                if not df.empty:
                    summary_data.append({
                        'Sector': sector,
                        'Candidates': len(df),
                        'Avg Market Cap ($B)': df['market_cap'].mean() / 1e9
                    })
            if summary_data:
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            for sector, df in self.sector_results.items():
                if not df.empty:
                    df.to_excel(writer, sheet_name=sector[:31], index=False)
        return output_file


class BaseSectorScreener:
    """Base class for sector-specific screening logic."""
    
    def __init__(self, sector_universe: pd.DataFrame, ai_service: AIService = None):
        self.universe = sector_universe
        self.sector_name = "Base"
        self.ai_service = ai_service
        self.deep_research = False
        self.defeatbeta_service = None
        
    def run_sector_funnel(self) -> pd.DataFrame:
        print(f"\n[Funnel] Starting universe: {len(self.universe)} stocks")
        quant_filtered = self.apply_quantitative_filters()
        print(f"[Funnel] Stage 1 (Broad Quant): {len(quant_filtered)} stocks remain.")
        
        if quant_filtered.empty: return quant_filtered

        if self.deep_research and self.defeatbeta_service:
            print(f"[Funnel] Stage 2 (Deep Quant): Fetching institutional data for top survivors...")
            research_data = {}
            for idx, row in quant_filtered.iterrows():
                ticker = row['ticker']
                research_data[ticker] = self.defeatbeta_service.get_deep_research(ticker)

            qual_filtered = self.apply_qualitative_filters(quant_filtered, research_data)
        else:
            qual_filtered = self._apply_ai_qualitative_analysis(quant_filtered)

        top_10 = self.rank_and_select(qual_filtered, n=10)
        return top_10
    
    def apply_quantitative_filters(self) -> pd.DataFrame:
        raise NotImplementedError
    
    def apply_qualitative_filters(self, df: pd.DataFrame, research_data: Dict = None) -> pd.DataFrame:
        return self._apply_ai_qualitative_analysis(df, research_data)
    
    def rank_and_select(self, df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        if 'composite_score' in df.columns:
            return df.nlargest(n, 'composite_score')
        return df.sample(min(n, len(df))) if not df.empty else df
    
    def _percentile_filter(self, df: pd.DataFrame, column: str, 
                          percentile: float, higher_is_better: bool = True) -> pd.DataFrame:
        if column not in df.columns or df[column].isna().all():
            return df
        threshold = df[column].quantile(percentile)
        return df[df[column] >= threshold] if higher_is_better else df[df[column] <= threshold]

    def _apply_ai_qualitative_analysis(self, df: pd.DataFrame, research_data: Dict = None) -> pd.DataFrame:
        print(f"  Running Institutional research analysis for {len(df)} {self.sector_name} stocks...")
        
        # [Sequential Mode] One at a time for maximum reliability
        for idx, row in df.iterrows():
            ticker = row['ticker']
            company = row.get('company_name', ticker)
            ticker_research = research_data.get(ticker, {}) if research_data else {}
            
            # Execute analysis
            idx, composite_score, institutional_metrics, ai_insights = self._process_single_stock_analysis(
                idx, ticker, company, ticker_research, row
            )
            
            # Save results
            df.at[idx, 'composite_score'] = composite_score
            for k, v in institutional_metrics.items(): df.at[idx, k] = v
            for k, v in ai_insights.items(): df.at[idx, k] = v
            
        return df

    def _process_single_stock_analysis(self, idx, ticker, company, ticker_research, row):
        transcripts = ticker_research.get('transcripts', [])
        insider_buying = ticker_research.get('insider_buying', False)
        sec_text = ticker_research.get('sec_text', '')
        ai_data = self.ai_service.analyze_equity_qualitative(
            ticker, company, self.sector_name, 
            transcripts=transcripts, 
            insider_buying=insider_buying,
            sec_text=sec_text
        )
        inst_metrics = {
            'fair_price': ticker_research.get('fair_price'),
            'dcf_upside': ticker_research.get('upside', 0),
            'roic': ticker_research.get('roic'),
            'beta_5y': ticker_research.get('beta'),
            'insider_buying': insider_buying
        }
        ai_insights = {
            'qual_sentiment': ai_data.get('overall_sentiment', 0),
            'sentiment_drift': ai_data.get('sentiment_drift', "stable"),
            'is_sandbagging': ai_data.get('is_sandbagging', False),
            'sandbagging_evidence': ai_data.get('sandbagging_evidence', "No specific evidence cited."),
            'catalysts': ", ".join(ai_data.get('catalysts', [])) if isinstance(ai_data.get('catalysts'), list) else ai_data.get('catalysts', ""),
            'risk_flags': ", ".join(ai_data.get('risk_flags', [])) if isinstance(ai_data.get('risk_flags'), list) else ai_data.get('risk_flags', ""),
            'ai_summary': ai_data.get('summary', "")
        }
        upside = ticker_research.get('upside', 0) or 0
        value_score = min(max(float(upside) * 100, 0), 100)
        sentiment_norm = (ai_data.get('overall_sentiment', 0) + 100) / 2
        drift_map = {"improving": 1.25, "stable": 1.0, "deteriorating": 0.5}
        ai_score = sentiment_norm * drift_map.get(ai_data.get('sentiment_drift'), 1.0)
        quality_metric = ticker_research.get('roic') or row.get('roe', 0.15) or 0.15
        quality_score = min(max(float(quality_metric) * 100 * 2, 0), 100) 
        composite = (value_score * 0.40) + (ai_score * 0.30) + (quality_score * 0.30)
        if insider_buying: composite *= 1.15
        if ai_data.get('is_sandbagging'): composite *= 1.10
        return idx, composite, inst_metrics, ai_insights


class ITSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame:
        return self._percentile_filter(self.universe.copy(), 'gross_margin', 0.60, True)

class FinancialsSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame:
        df = self.universe.copy()
        if 'rotce' in df.columns and not df['rotce'].isna().all():
            df = self._percentile_filter(df, 'rotce', 0.50, True)
        elif 'roe' in df.columns:
            df = self._percentile_filter(df, 'roe', 0.50, True)
            
        if 'price_to_tbv' in df.columns and not df['price_to_tbv'].isna().all():
            df = self._percentile_filter(df, 'price_to_tbv', 0.50, False)
        elif 'price_to_book' in df.columns:
            df = self._percentile_filter(df, 'price_to_book', 0.50, False)
        return df

class HealthCareSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame:
        return self._percentile_filter(self.universe.copy(), 'gross_margin', 0.60, True)

class ConsumerDiscSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame:
        df = self.universe.copy()
        if 'comp_sales_growth' in df.columns: df = self._percentile_filter(df, 'comp_sales_growth', 0.50, True)
        return df

class CommServicesSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame:
        df = self.universe.copy()
        if 'fcf_yield' in df.columns: df = self._percentile_filter(df, 'fcf_yield', 0.60, True)
        return df

class IndustrialsSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame: return self.universe.copy()

class ConsumerStaplesSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame: return self.universe.copy()

class EnergySectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame: return self.universe.copy()

class UtilitiesSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame: return self.universe.copy()

class RealEstateSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame: return self.universe.copy()

class MaterialsSectorScreener(BaseSectorScreener):
    def apply_quantitative_filters(self) -> pd.DataFrame: return self.universe.copy()
