# AI-Native Fundamental Equity Screening Agent

A production-ready system for screening the entire US equity universe ($1B-$50B market cap) using sector-specific fundamental filters to identify 10 highest-conviction names per sector for deep diligence.

## Overview

This system implements a **three-stage funnel** for each of the 11 GICS sectors:

1. **Dynamic Quantitative Filters**: Percentile-based screening on financial metrics
2. **Dynamic Qualitative Filters**: NLP analysis of earnings transcripts and SEC filings  
3. **Ranking & Selection**: Composite scoring to select top 10 names per sector

**Output**: 110 stocks total (10 per sector) ready for full fundamental research and modeling.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Ingestion Layer                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  CapIQ API │  │ Bloomberg  │  │ Yahoo Fin  │            │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘            │
│         │                │                │                  │
│         └────────────────┴────────────────┘                  │
│                          │                                   │
│                    Universe Builder                          │
│              (5,000 stocks → ~1,300 after mcap filter)       │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Sector-by-Sector Screening Engine              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Information Technology (180 stocks)                 │   │
│  │    Stage 1: Quant Filters    → 60 stocks            │   │
│  │    Stage 2: Qual Filters     → 15 stocks            │   │
│  │    Stage 3: Ranking          → 10 stocks ✓          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [Repeat for all 11 GICS sectors]                           │
│                                                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Output Generation                         │
│  • Excel file with 11 sector sheets (10 stocks each)        │
│  • CSV summaries for further analysis                       │
│  • JSON data for downstream modeling pipelines              │
└──────────────────────────────────────────────────────────────┘
```

---

## Sector-Specific Filters

### Information Technology
**Quantitative:**
- Gross margin: Top 40th percentile
- Revenue growth deceleration: Bottom 60th percentile  
- Customer concentration: Exclude top 25th percentile

**Qualitative:**
- NLP scan for: "customer wins", "pipeline acceleration", "product-market fit"
- Churn commentary vs. NRR validation
- Cloud migration penetration analysis

### Financials
**Quantitative:**
- ROTCE: Top 50th percentile
- P/TBV: Bottom 50th percentile (cheaper)
- NPL trend: Exclude top 30th percentile (worst credit)

**Qualitative:**
- Credit quality divergence detection
- Deposit franchise language ("sticky", "core")
- Loan growth guidance vs. consensus gaps

### Health Care
**Quantitative:**
- Pipeline maturity score: Top 50th percentile
- Patent cliff risk: Exclude top 20th percentile
- Gross margin: Top 40th percentile

**Qualitative:**
- Trial readout timing not in models
- Reimbursement sentiment shifts
- Commercial execution confidence language

[See full sector specifications in `equity_screener_agent.py`]

---

## Installation

### Requirements
```bash
pip install pandas numpy yfinance requests openpyxl --break-system-packages
```

### Optional (for production):
```bash
# For CapIQ integration
pip install capiq-python --break-system-packages

# For Bloomberg integration  
pip install blpapi --break-system-packages

# For advanced NLP (recommended)
pip install transformers torch nltk --break-system-packages
```

---

## Quick Start

### Option 1: Using Yahoo Finance (Free, Development)
```bash
python run_screener.py --data-source yfinance
```

This will:
1. Download S&P 500 constituent data
2. Filter to $1B-$50B market cap
3. Run sector-by-sector screening
4. Output results to `/mnt/user-data/outputs/`

**Runtime**: ~10-15 minutes for full S&P 500

### Option 2: Using CSV Input
1. Prepare `universe.csv` with columns:
   ```
   ticker, company_name, sector, market_cap, price, [financial metrics...]
   ```

2. Run screener:
   ```bash
   python run_screener.py --data-source csv
   ```

### Option 3: Production (CapIQ/Bloomberg)
```bash
# Configure credentials in data_ingestion.py
python run_screener.py --data-source capiq
```

---

## Usage Examples

### Basic Screening
```python
from run_screener import ProductionScreener

screener = ProductionScreener(data_source='yfinance')
results = screener.run_full_pipeline()

# Access sector results
it_stocks = results['Information Technology']
print(it_stocks[['ticker', 'company_name', 'market_cap']])
```

### Custom Market Cap Range
```python
screener = ProductionScreener(data_source='yfinance')
screener.min_mcap = 5e9   # $5B
screener.max_mcap = 25e9  # $25B
results = screener.run_full_pipeline()
```

### Analyzing NLP Results
```python
from nlp_analysis import TranscriptAnalyzer

# Analyze earnings call transcript
analyzer = TranscriptAnalyzer("Information Technology")
transcript = "..."  # Your transcript text

analysis = analyzer.analyze_transcript(transcript)
print(f"Sentiment: {analysis['overall_sentiment']}")
print(f"Confidence: {analysis['confidence_score']}")
print(f"Catalysts: {analysis['catalyst_mentions']}")
```

---

## Output Files

### Main Excel File
**Format**: `equity_screen_YYYYMMDD_HHMMSS.xlsx`

**Sheets**:
- `Summary`: Overview of all sectors
- `Information Technology`: 10 IT stocks
- `Financials`: 10 Financial stocks
- ... (11 sheets total)

**Columns** (example for IT):
```
ticker | company_name | sector | market_cap | gross_margin | 
revenue_growth | customer_concentration | composite_score | ...
```

### Summary CSV
**Format**: `screening_summary_YYYYMMDD_HHMMSS.csv`

All 110 stocks in single file for easy sorting/filtering.

### Individual Sector CSVs
One CSV per sector for targeted analysis:
```
Information_Technology_YYYYMMDD_HHMMSS.csv
Financials_YYYYMMDD_HHMMSS.csv
...
```

---

## Customization

### Adding Custom Metrics

1. **Modify data ingestion** (`data_ingestion.py`):
```python
def get_fundamentals(self, tickers):
    # Add your custom metric
    fields = [
        "IQ_MARKETCAP",
        "YOUR_CUSTOM_METRIC"  # Add here
    ]
```

2. **Add to sector filter** (`equity_screener_agent.py`):
```python
def apply_quantitative_filters(self):
    df = self.universe.copy()
    
    # Add your filter
    df = self._percentile_filter(df, 'your_metric', 0.60, higher_is_better=True)
    
    return df
```

### Adding New Sectors

If you want to subdivide GICS sectors (e.g., separate Software from Hardware):

1. Define new sector in `GICS_SECTORS` list
2. Create new `SectorScreener` class
3. Implement `apply_quantitative_filters()` and `apply_qualitative_filters()`

---

## Production Deployment

### Recommended Architecture

```
Daily Cron Job (6 AM ET):
  ├─ Data Refresh: Pull latest fundamentals from CapIQ
  ├─ Universe Update: Adjust for IPOs, delistings
  ├─ Run Screening: Execute full pipeline
  └─ Email Results: Send Excel to analysts

Weekly Deep Dive (Mondays):
  ├─ Fetch Earnings Transcripts (last week's)
  ├─ Run NLP Analysis
  ├─ Update Qualitative Scores
  └─ Flag High-Priority Names
```

### Data Sources

**Development**:
- Yahoo Finance (free, rate-limited)
- SEC EDGAR (free, official filings)

**Production**:
- S&P Capital IQ (comprehensive fundamentals)
- Bloomberg Terminal (real-time data + filings)
- FactSet (alternative to CapIQ)
- AlphaSense (transcript aggregator)

---

## Performance Optimization

### For Large Universes (>2,000 stocks)

1. **Parallelize sector screening**:
```python
from multiprocessing import Pool

def screen_sector(sector):
    screener = get_sector_screener(sector)
    return screener.run_sector_funnel()

with Pool(11) as p:  # 11 GICS sectors
    results = p.map(screen_sector, GICS_SECTORS)
```

2. **Cache fundamental data**:
```python
# Save fundamentals to local DB
universe.to_parquet('universe_cache.parquet')

# Load on subsequent runs
universe = pd.read_parquet('universe_cache.parquet')
```

3. **Incremental updates**:
- Only re-screen stocks with recent earnings
- Keep prior results for unchanged names

---

## Troubleshooting

### "No stocks in universe"
- Check data source credentials
- Verify market cap range is not too restrictive
- Ensure tickers are formatted correctly (e.g., 'BRK-B' not 'BRK.B')

### "Percentile filter returns empty DataFrame"
- Column may be missing from data
- Check for NaN values: `df['column'].isna().sum()`
- Verify column names match between data source and filters

### Yahoo Finance rate limiting
- Add delays: `time.sleep(0.5)` between requests
- Use smaller batches: Process 50 tickers at a time
- Consider upgrading to paid data source

---

## Next Steps

Once you have your 110 candidates (10 per sector):

1. **Build 3-statement models** for each name
2. **Conduct primary research**:
   - Expert network calls
   - Channel checks  
   - Customer interviews
   - Competitor analysis

3. **Rank by conviction**:
   - Thesis differentiation
   - Catalyst timing
   - Risk/reward asymmetry
   - Information edge

4. **Select final positions**:
   - Target: 5-10 highest conviction longs/shorts
   - Ensure sector diversification
   - Size by conviction level

---

## File Structure

```
.
├── equity_screener_agent.py    # Main screening engine
├── data_ingestion.py            # Data provider connectors
├── nlp_analysis.py              # Transcript/filing analysis
├── run_screener.py              # Production orchestrator
├── README.md                    # This file
└── outputs/                     # Results directory
    ├── equity_screen_*.xlsx
    ├── screening_summary_*.csv
    └── [Sector]_*.csv
```

---

## Contributing

To add new features:

1. **New data sources**: Implement `DataProvider` interface in `data_ingestion.py`
2. **New NLP models**: Add analyzer classes in `nlp_analysis.py`
3. **New sectors**: Inherit from `BaseSectorScreener` in `equity_screener_agent.py`

---

## License

Proprietary - NYU Stern Quantitative Finance Society

---

## Contact

For questions or issues:
- **Developer**: [Your Name]
- **Organization**: NYU QFS Long/Short Portfolio
- **Documentation**: [Link to internal wiki]

---

## Changelog

**v1.0.0** (2026-04-03)
- Initial release
- 11 GICS sectors implemented
- Yahoo Finance integration for development
- Basic NLP sentiment analysis
- Excel/CSV output generation

**Planned Features**:
- [ ] FinBERT integration for advanced sentiment
- [ ] Alternative data connectors (web traffic, job postings)
- [ ] Automated thesis generation using LLMs
- [ ] Slack/email alerting for new candidates
- [ ] Backtesting framework for filter optimization
