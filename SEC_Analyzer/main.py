#!/opt/homebrew/bin/python3.12
import time
import logging
from datetime import datetime
from sheets_processor import SheetsProcessor
from financial_analyzer import FinancialAnalyzer

# ------------------------------------------------------------------ #
#  Logging setup                                                       #
# ------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    handlers=[
        logging.FileHandler(f"run_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Output column schema                                                #
# ------------------------------------------------------------------ #
HEADERS = [
    # Identity
    'Ticker', 'Name', 'Market Cap',
    # Returns & Growth
    'Rev CAGR (3Y)', 'Net Income CAGR',
    'ROE', 'ROIC', 'WACC',
    # Risk & Quant Scores
    'Piotroski F-Score', 'Altman Z-Score',
    # SEC Intelligence (NEW)
    'Net Insider (6M)', 'Top Holders', 'Product Segments', 'Geo Segments',
    'Latest Filing',
    # Valuation
    'P/E', 'PEG', 'P/Book',
    # Sentiment & Thesis
    'Overall Sentiment', 'Investment Thesis',
]


def analysis_to_row(a: dict) -> list:
    """Map analysis dict → ordered row list matching HEADERS."""
    return [
        a.get('ticker', ''),
        a.get('name', ''),
        a.get('market_cap', ''),
        a.get('rev_cagr', ''),
        a.get('ni_cagr', ''),
        a.get('roe', ''),
        a.get('roic', ''),
        a.get('wacc', ''),
        a.get('f_score', ''),
        a.get('z_score', ''),
        a.get('insider_sentiment', ''),
        a.get('top_holders', ''),
        a.get('segments', ''),
        a.get('geos', ''),
        a.get('filing_url', ''),
        a.get('pe_ratio', ''),
        a.get('peg_ratio', ''),
        a.get('price_to_book', ''),
        a.get('overall_sentiment', ''),
        a.get('summary', ''),
    ]


# ------------------------------------------------------------------ #
#  Main                                                                #
# ------------------------------------------------------------------ #

def main():
    log.info("=" * 60)
    log.info("SEC Analyzer — Starting run")
    log.info("=" * 60)

    sheets   = SheetsProcessor()
    analyzer = FinancialAnalyzer()

    log.info("Fetching tickers from source Google Sheet...")
    all_tabs_data = sheets.get_all_tickers_by_tab()
    log.info(f"Found {len(all_tabs_data)} sector tab(s)")

    sector_summaries = []

    for tab_idx, (tab_name, tickers) in enumerate(all_tabs_data.items()):
        log.info(f"\n[{tab_idx+1}/{len(all_tabs_data)}] Processing sector: {tab_name} ({len(tickers)} tickers)")

        tab_results  = []
        bullish_cnt  = 0
        bearish_cnt  = 0
        neutral_cnt  = 0
        f_scores     = []
        z_scores     = []

        for i, source_row in enumerate(tickers):
            ticker = source_row['ticker']
            name   = source_row.get('name', '')
            log.info(f"  [{i+1}/{len(tickers)}] {ticker} – {name}")

            try:
                analysis = analyzer.analyze_ticker(ticker, name, source_row)
                if analysis:
                    # Carry through any EBITDA margin from source row
                    if 'ebitda_margin' not in analysis or not analysis['ebitda_margin']:
                        analysis['ebitda_margin'] = source_row.get('ebitda_margin', '')

                    tab_results.append(analysis_to_row(analysis))

                    # Aggregate for summary
                    sentiment = str(analysis.get('overall_sentiment', '')).lower()
                    if 'bull' in sentiment:  bullish_cnt += 1
                    elif 'bear' in sentiment: bearish_cnt += 1
                    else:                     neutral_cnt += 1

                    try:    f_scores.append(int(analysis['f_score']))
                    except: pass
                    try:    z_scores.append(float(analysis['z_score']))
                    except: pass

                else:
                    log.warning(f"    Skipping {ticker} — no data returned")

            except Exception as e:
                log.error(f"    Error processing {ticker}: {e}")

            time.sleep(1.5)  # polite delay between tickers

        # Write sector tab
        if tab_results:
            log.info(f"Writing {len(tab_results)} rows to target tab '{tab_name}'")
            sheets.write_tab_data(tab_name, HEADERS, tab_results)
        else:
            log.warning(f"No results for tab '{tab_name}'")

        # Collect sector summary stats
        sector_summaries.append({
            'sector':        tab_name,
            'total_tickers': len(tab_results),
            'avg_f_score':   f"{sum(f_scores)/len(f_scores):.1f}" if f_scores else 'N/A',
            'avg_z_score':   f"{sum(z_scores)/len(z_scores):.2f}" if z_scores else 'N/A',
            'bullish_count': bullish_cnt,
            'bearish_count': bearish_cnt,
            'neutral_count': neutral_cnt,
        })

    # Write summary tab
    log.info("\nWriting Summary tab...")
    sheets.write_summary_tab(sector_summaries)

    log.info("\n" + "=" * 60)
    log.info("Run complete. Check target Google Sheet.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
