# Earnings Call Analyzer - Streamlined Edition

**Fetch past 4 earnings calls → Generate detailed summaries → Write to Google Sheets**

Clean, actionable output: **4 columns** (one detailed summary per EC)

---

## What You Get

Your Google Sheet will have **4 new columns** added for each ticker:

| Ticker | ... | Q4 2024 Summary | Q3 2024 Summary | Q2 2024 Summary | Q1 2024 Summary |
|--------|-----|-----------------|-----------------|-----------------|-----------------|
| AAPL   | ... | [Detailed paragraph covering revenue growth, management tone, guidance, drivers, risks, and investment signal] | [EC summary] | [EC summary] | [EC summary] |

Each summary is a **200-300 word comprehensive analysis** written for portfolio managers who need quick, actionable takeaways.

---

## Data Sources

Transcripts are pulled from (in priority order):

1. **Seeking Alpha** - Web scraping earnings transcript pages
2. **Motley Fool** - Fallback if SA doesn't have coverage
3. Manual upload - You can add your own transcripts later

No Quartr API required - fully automated web scraping.

---

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Google Sheets API Setup

**A. Create Service Account**
1. Go to https://console.cloud.google.com/
2. Create project → Enable Google Sheets API
3. Create Service Account → Download JSON key
4. Save as `credentials.json` in this folder

**B. Share Your Sheet**
1. Open your Google Sheet
2. Share with the service account email (from credentials.json)
3. Give Editor access

### 3. Configure
```bash
cp .env.example .env
```

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
SHEET_ID=your_sheet_id_here
```

### 4. Run
```bash
# Test with mock data first
python earnings_call_analyzer.py
> mock

# Then run for real
python earnings_call_analyzer.py
> real
```

---

## Output Format

Each earnings call summary includes:

✅ **Revenue growth and key financial metrics**
✅ **Management tone and sentiment analysis**  
✅ **Forward guidance vs expectations**
✅ **Key growth drivers and business highlights**
✅ **Major risks, headwinds, or concerns**
✅ **Overall investment signal** (bullish/neutral/bearish)

Written as flowing prose, not bullet points - easy to read and scan.

---

## Cost Estimate

**Per earnings call:**
- Input: ~20k tokens (transcript) = $0.06
- Output: ~400 tokens (summary) = $0.006
- **Total: ~$0.07 per EC**

**For 10 tickers × 4 ECs:** ~$2.80
**For 110 tickers × 4 ECs:** ~$30.80

---

## Processing Time

With 20s delays between API calls:
- Each ticker: ~1.5 minutes
- 10 tickers: ~15 minutes
- 110 tickers: ~2.5 hours

---

## How It Works

```
1. Read tickers from Google Sheet
         ↓
2. For each ticker:
   - Scrape Seeking Alpha for transcripts
   - Fallback to Motley Fool if needed
         ↓
3. For each transcript found:
   - Send to Claude for detailed analysis
   - Get 200-300 word comprehensive summary
         ↓
4. Write 4 summaries as new columns
   (same row as ticker)
```

---

## Troubleshooting

**"No transcripts found"**
- Normal for some tickers (not all companies have public transcripts)
- Analyzer writes "No transcript available" and continues

**"Google Sheets auth failed"**
- Verify `credentials.json` is in the directory
- Check service account is shared on your sheet

**"Rate limit hit"**
- Increase `REQUEST_DELAY_SECONDS` in .env
- Default 20s is safe for most API tiers

**Web scraping returns no text**
- Seeking Alpha/Motley Fool may have changed their HTML structure
- Check if ticker has earnings transcripts on those sites
- You can manually add transcripts and modify the code to read from files

---

## Files

- `earnings_call_analyzer.py` - Main script with web scraping + Claude analysis
- `requirements.txt` - Python dependencies
- `.env.example` - Configuration template
- `credentials.json` - Your Google service account (YOU CREATE THIS)

---

## Next Steps

1. ✅ Run in mock mode to verify setup
2. ✅ Test on 1-2 real tickers
3. ✅ Run on full ticker list
4. 📊 Read summaries to identify variant perception opportunities
5. 🚀 Build conviction scoring based on EC signals

---

## Support

Need help? Check:
1. `.env` is configured with valid keys
2. `credentials.json` exists and service account is shared
3. Your sheet has a column named exactly "Ticker"
4. Run mock mode first to isolate issues

---

**Built for Alpha OS Research Platform**
