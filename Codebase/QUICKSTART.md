# Earnings Call Analyzer - Quick Start Guide

## Installation

```bash
# 1. Install required packages
pip install pandas openpyxl requests

# 2. Set your API key
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

## Usage

```bash
# Basic usage
python earnings_call_analyzer.py input.xlsx

# Specify output file
python earnings_call_analyzer.py screening_results.xlsx analyzed_output.xlsx

# One-liner with API key
ANTHROPIC_API_KEY="sk-ant-..." python earnings_call_analyzer.py input.xlsx
```

## Input Format

Your Excel file must have at minimum:
- `Ticker` column (required)
- `Company Name` or `Company` column (recommended)

Example:
```
Ticker | Company Name          | Industry       | Score
-------|----------------------|----------------|------
NVDA   | NVIDIA Corporation   | Semiconductors | 8.5
MSFT   | Microsoft Corp       | Software       | 8.2
```

## Output Columns

The analyzer adds 14 new columns with `EC_` prefix:

| Column | Description |
|--------|-------------|
| `EC_Transcript_URL` | Source URL of earnings call |
| `EC_Date` | Date/quarter of call |
| `EC_Forward_Guidance` | Management's outlook |
| `EC_Strategic_Initiatives` | Key strategic moves |
| `EC_Analyst_Questions` | Main Q&A themes |
| `EC_Mgmt_Response_Tone` | Tone assessment |
| `EC_Beat_Miss` | Beat/miss vs expectations |
| `EC_Margin_Commentary` | Margin/profitability notes |
| `EC_Capex_Plans` | Capital expenditure plans |
| `EC_Competitive_Position` | Competitive positioning |
| `EC_Risk_Flags` | Red flags identified |
| `EC_Key_Takeaways` | Summary bullet points |
| `EC_Overall_Sentiment` | Bullish/Neutral/Bearish |
| `EC_Analysis_Timestamp` | When analyzed |

## Performance

- **~20-30 seconds per company** (web search + analysis)
- **3-second delay** between API calls (rate limiting)
- For 10 companies: ~5 minutes
- For 50 companies: ~25 minutes

## Example Session

```bash
$ export ANTHROPIC_API_KEY="sk-ant-..."

$ python earnings_call_analyzer.py my_screening.xlsx

================================================================================
EARNINGS CALL ANALYZER
================================================================================
Input:  my_screening.xlsx
Output: my_screening_with_earnings.xlsx
================================================================================

📊 Found 5 companies to analyze

[1/5] NVDA - NVIDIA Corporation
    ✅ Bullish - Strong AI datacenter demand, raised guidance
       https://seekingalpha.com/article/4734567-nvidia-nvda-q4-2...

[2/5] MSFT - Microsoft Corporation
    ✅ Bullish - Azure growth accelerating, AI monetization strong
       https://seekingalpha.com/article/4733821-microsoft-msft-...

[3/5] TSLA - Tesla Inc.
    ⚠️  No transcript found

================================================================================
SUMMARY
================================================================================
Total companies:       5
✅ Analyzed:           4
⚠️  No transcript:      1
❌ Failed:             0
================================================================================
```

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### "Analysis Failed"
- Check API key is valid
- Check internet connection
- API might be rate limited (wait a few minutes)

### "Not Found"
- Normal for companies without recent earnings calls
- Older/smaller companies may not have transcripts online
- Try checking Seeking Alpha manually

### Slow performance
- Each company requires web search + full analysis
- 3-second delay between calls is intentional (rate limiting)
- Run smaller batches for testing

## API Costs

Using Claude Sonnet 4:
- **Input**: ~$3 per million tokens
- **Output**: ~$15 per million tokens

Typical per company:
- ~10K input tokens (search + transcript) = $0.03
- ~1K output tokens (analysis) = $0.015
- **Total: ~$0.04-0.05 per company**

For 100 companies: ~$4-5 in API costs

## Tips

1. **Test on small batch first** (5-10 companies)
2. **Run overnight** for large batches (50+ companies)
3. **Check output** after first few to ensure quality
4. **Save intermediate results** - output file is updated progressively
5. **Rerun failures** - you can rerun on same file, it will update rows

## Integration with Screening Funnel

```python
# After your screening funnel generates results:
import subprocess

# Run earnings analyzer
subprocess.run([
    'python', 'earnings_call_analyzer.py',
    'screening_output.xlsx',
    'final_analysis.xlsx'
])

# Now use final_analysis.xlsx in your research pipeline
```
