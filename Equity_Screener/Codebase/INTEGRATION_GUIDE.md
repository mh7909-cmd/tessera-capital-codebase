# Earnings Call Analyzer - Integration Setup

## Files to Copy to Your Equity Screener Directory

Copy these 4 files into your equity screener folder (where `run_screener.py` is):

```
equity_screener/
├── earnings_call_analyzer.py      ← Copy this
├── analyze_latest_screening.py    ← Copy this  
├── run_full_pipeline.py           ← Copy this
├── QUICKSTART.md                  ← Copy this (reference)
└── [your existing files]
```

## Quick Start - 3 Ways to Use

### Option 1: Analyze Existing Screening (Simplest)
```bash
cd equity_screener
export ANTHROPIC_API_KEY="sk-ant-..."

# Auto-finds latest equity_screen_*.xlsx file
python analyze_latest_screening.py

# Or specify file
python analyze_latest_screening.py equity_screen_20260403_192718.xlsx
```

### Option 2: Full Pipeline (Screening + Earnings)
```bash
cd equity_screener
export ANTHROPIC_API_KEY="sk-ant-..."

# Run both screening and earnings analysis
python run_full_pipeline.py

# With industry filter
python run_full_pipeline.py --industry Technology

# Skip screening, analyze existing results
python run_full_pipeline.py --skip-screening
```

### Option 3: Direct Command (Most Control)
```bash
cd equity_screener
export ANTHROPIC_API_KEY="sk-ant-..."

# Analyze specific file
python earnings_call_analyzer.py equity_screen_20260403_192718.xlsx output.xlsx
```

## What Gets Generated

For input file: `equity_screen_20260403_192718.xlsx`

Output file: `equity_screen_20260403_192718_with_earnings.xlsx`

### New Columns Added (14 total):
- `EC_Transcript_URL` - Source link
- `EC_Date` - Call date/quarter
- `EC_Forward_Guidance` - Outlook
- `EC_Strategic_Initiatives` - Key moves
- `EC_Analyst_Questions` - Q&A themes
- `EC_Mgmt_Response_Tone` - Tone assessment
- `EC_Beat_Miss` - Beat/miss expectations
- `EC_Margin_Commentary` - Margin notes
- `EC_Capex_Plans` - Investment plans
- `EC_Competitive_Position` - Competitive positioning
- `EC_Risk_Flags` - Red flags
- `EC_Key_Takeaways` - Summary points
- `EC_Overall_Sentiment` - Bullish/Neutral/Bearish
- `EC_Analysis_Timestamp` - Analysis time

## Example Workflow

```bash
# 1. Set API key (do this once per terminal session)
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# 2. Run your screener as usual
python run_screener.py
# Output: equity_screen_20260404_120000.xlsx

# 3. Analyze earnings calls
python analyze_latest_screening.py
# Output: equity_screen_20260404_120000_with_earnings.xlsx

# 4. Open Excel, filter/sort by:
#    - EC_Overall_Sentiment = "Bullish"
#    - EC_Risk_Flags = (empty or short)
#    - High conviction scores

# 5. Begin primary research on top names
```

## Performance & Costs

- **Time**: ~25 seconds per company
- **Rate limit**: 3 seconds between API calls
- **API cost**: ~$0.04-0.05 per company

### Batch Sizes:
- 10 companies: ~5 minutes, ~$0.50
- 25 companies: ~12 minutes, ~$1.25
- 50 companies: ~25 minutes, ~$2.50
- 100 companies: ~50 minutes, ~$5.00

## Filtering Results in Excel

After analysis completes, use Excel filters:

### High-Conviction Bullish Names:
1. Filter `EC_Overall_Sentiment` contains "Bullish"
2. Filter `EC_Risk_Flags` length < 100 chars (minimal risks)
3. Sort by your original `Score` column descending

### Beat & Raise Names:
1. Filter `EC_Beat_Miss` contains "Beat" or "beat"
2. Filter `EC_Forward_Guidance` contains "raised" or "raise"

### Red Flags to Investigate:
1. Filter `EC_Risk_Flags` length > 200 chars
2. Review `EC_Mgmt_Response_Tone` = "Defensive" or "Evasive"

## Advanced: Modify Analysis Fields

Edit `earnings_call_analyzer.py` line 40-65 to customize what Claude analyzes.

Example - add a new field for "Insider Buying/Selling Mentioned":
```python
# In the prompt JSON format, add:
"insider_activity": "Any mention of insider buying/selling (max 100 chars)"

# Then add to columns (line 165):
'EC_Insider_Activity',

# And populate (line 210):
df.at[idx, 'EC_Insider_Activity'] = analysis.get('insider_activity', '')[:200]
```

## Troubleshooting

### Import Error
```
❌ earnings_call_analyzer.py not found
```
→ Make sure you copied the file to your equity_screener directory

### API Key Error
```
❌ ANTHROPIC_API_KEY not set
```
→ Run: `export ANTHROPIC_API_KEY="sk-ant-..."`

### No Transcripts Found
```
⚠️ No transcript found
```
→ Normal for companies without recent earnings calls
→ Smaller/private companies may not publish transcripts online

### Analysis Failed
```
❌ Analysis failed
```
→ Check internet connection
→ Verify API key is valid
→ Check API rate limits (wait 5 minutes)

## Next Steps After Analysis

1. **Review Output Excel**
   - Sort by sentiment
   - Identify high-conviction names
   
2. **Primary Research**
   - Call IR for transcript links not found
   - Deep dive on bullish names with low risk flags
   
3. **Build Positions**
   - Use Kelly Criterion sizing based on conviction
   - Monitor earnings for position sizing changes

4. **Track Performance**
   - Compare EC_Overall_Sentiment vs actual stock performance
   - Calibrate conviction scores over time

## Integration with Your Workflow

Add to your daily/weekly research routine:

```bash
# Morning routine
cd ~/equity_screener

# 1. Run overnight screen
python run_screener.py > logs/screen_$(date +%Y%m%d).log

# 2. Analyze earnings (run in background)
nohup python analyze_latest_screening.py > logs/earnings_$(date +%Y%m%d).log 2>&1 &

# 3. Check back in 20 min, review results
```

## Questions?

Check QUICKSTART.md for detailed usage examples and tips.
