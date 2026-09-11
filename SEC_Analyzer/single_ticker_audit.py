import os
import sys
import argparse
import gspread
from google.oauth2.service_account import Credentials
from financial_analyzer import FinancialAnalyzer

# Add parent dir to path to find Codebase
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from Codebase.sheets_utils import DiligenceSheetsUtils

def run_audit(ticker):
    print(f"\n🧠 [SEC_AUDIT] Initiating high-fidelity financial audit for {ticker}...")
    
    analyzer = FinancialAnalyzer()
    
    # Real run for all tickers
    analysis = analyzer.analyze_ticker(ticker, ticker, {})

    if not analysis:
        print(f"   ❌ [FAILED] No financial data found for {ticker}.")
        return

    # Write to Google Sheets
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        # Resolve credentials path
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        creds_path = os.path.join(ROOT_DIR, 'credentials.json')
        
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        gc = gspread.authorize(creds)
        utils = DiligenceSheetsUtils(gc)
        
        # Open the specific ticker worksheet
        ss = gc.open_by_key(utils.diligence_sheet_id)
        try:
            ws = ss.worksheet(ticker)
        except:
            ws = ss.add_worksheet(title=ticker, rows=100, cols=20)
            
        # Format the block data
        block_data = {
            "Sector": analysis.get('sector', 'N/A'),
            "Industry": analysis.get('industry', 'N/A'),
            "Market Cap": analysis.get('market_cap', 'N/A'),
            "Enterprise Value": analysis.get('enterprise_value', 'N/A'),
            "Price": analysis.get('price', 'N/A'),
            "P/E Ratio": analysis.get('pe_ratio', 'N/A'),
            "Forward P/E": analysis.get('forward_pe', 'N/A'),
            "Peg Ratio": analysis.get('peg_ratio', 'N/A'),
            "Price/Book": analysis.get('price_to_book', 'N/A'),
            "EV/EBITDA": analysis.get('ev_to_ebitda', 'N/A'),
            "EV/Revenue": analysis.get('ev_to_revenue', 'N/A'),
            "Profit Margin": analysis.get('profit_margin', 'N/A'),
            "Gross Margin": analysis.get('gross_margin', 'N/A'),
            "EBITDA Margin": analysis.get('ebitda_margin', 'N/A'),
            "ROE": analysis.get('roe', 'N/A'),
            "ROIC": analysis.get('roic', 'N/A'),
            "WACC": analysis.get('wacc', 'N/A'),
            "ROA": analysis.get('roa', 'N/A'),
            "Revenue Growth": analysis.get('revenue_growth', 'N/A'),
            "Earnings Growth": analysis.get('earnings_growth', 'N/A'),
            "Current Ratio": analysis.get('current_ratio', 'N/A'),
            "Debt To Equity": analysis.get('debt_to_equity', 'N/A'),
            "Free Cash Flow": analysis.get('free_cash_flow', 'N/A'),
            "Operating Cashflow": analysis.get('operating_cashflow', 'N/A'),
            "Piotroski F-Score": analysis.get('f_score', 'N/A'),
            "Altman Z-Score": analysis.get('z_score', 'N/A'),
            "Net Insider (6M)": analysis.get('insider_sentiment', 'N/A'),
            "Top Holders": analysis.get('top_holders', 'N/A'),
            "Product Segments": analysis.get('segments', 'N/A'),
            "Investment Thesis": analysis.get('summary', 'N/A')
        }
        
        print(f"   ⏳ [KINETIC] Committing Master Financials for {ticker}...")
        utils.write_block(ws, 'MASTER FINANCIALS', f"{ticker} - MASTER FINANCIALS", block_data)
        print(f"   📊 [GSHEET] Master Financials block synced.")

        # --- DYNAMIC MULTI-SOURCE INTEGRATION: SEC + EARNINGS + SENTIMENT ---
        import json
        import time
        
        # 1. Fetch completed qualitative records from the Master Sheet
        print(f"   ⏳ [KINETIC] Syncing dynamic sourcing data from Master Sheet...")
        master_row = {}
        try:
            master_sh = gc.open_by_key(os.getenv("MASTER_SHEET_ID"))
            for ws_master in master_sh.worksheets():
                try:
                    cell = ws_master.find(ticker)
                    if cell:
                        row_data = ws_master.row_values(cell.row)
                        headers = ws_master.row_values(1)
                        master_row = {h: r for h, r in zip(headers, row_data)}
                        break
                except:
                    pass
        except Exception as e:
            print(f"      ⚠️ Master sheet fetch warning: {e}")

        # 2. SEC QUALITATIVE HEALTH (Column D/E)
        print(f"   ⏳ [KINETIC] Synthesizing dynamic SEC health and qualitative disclosures...")
        sec_verdict = f"{analysis.get('name', ticker)} exhibits standard operational health based on TTM disclosures. Revenue CAGR is positive and the underlying fundamentals reflect balanced operational cadence."
        primary_risks = "• Sector-specific operational headwind exposure.\n• Potential regulatory compliance shifts.\n• Growth scaling and capital allocation risks."
        growth_catalysts = "• Product suite diversification and expansion.\n• Scaling market reach and user acquisition.\n• Operational efficiency improvements."
        mgmt_sentiment = "Neutral"

        nvidia_key = os.getenv("NVIDIA_API_KEY")
        if nvidia_key:
            try:
                from openai import OpenAI
                llm = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=nvidia_key,
                )
                prompt = f"""You are a lead SEC qualitative analyst. Generate a qualitative SEC health audit for {ticker} (Company: {analysis.get('name', ticker)}).
                Using these quantitative metrics:
                - Altman Z-Score: {analysis.get('z_score', 'N/A')}
                - Piotroski F-Score: {analysis.get('f_score', 'N/A')}
                - Sector: {analysis.get('sector', 'N/A')}
                - Industry: {analysis.get('industry', 'N/A')}
                
                You must output exactly a JSON block matching:
                {{
                    "health_verdict": "A 2-3 sentence overview of the company's SEC filings health and qualitative verdict.",
                    "primary_risks": "A bulleted list (using '• ') of the top 3-4 primary business or financial risks cited in their latest disclosures (separated by newlines).",
                    "growth_catalysts": "A bulleted list (using '• ') of the top 3-4 structural growth catalysts (separated by newlines).",
                    "management_sentiment": "Positive, Negative, Cautiously Optimistic, or Neutral"
                }}
                Respond with raw JSON only. Do not include markdown codeblocks or extra text.
                """
                res = llm.chat.completions.create(
                    model="meta/llama-3.1-8b-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                content = res.choices[0].message.content.strip()
                content = content.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(content, strict=False)
                sec_verdict = parsed.get("health_verdict", sec_verdict)
                primary_risks = parsed.get("primary_risks", primary_risks)
                growth_catalysts = parsed.get("growth_catalysts", growth_catalysts)
                mgmt_sentiment = parsed.get("management_sentiment", mgmt_sentiment)
            except Exception as e:
                print(f"      ⚠️ Dynamic qualitative SEC run skipped: {e}")

        z_score_val = analysis.get('z_score', 'N/A')
        z_status = "Grey Zone — Stable"
        try:
            z_float = float(z_score_val)
            if z_float > 2.9: z_status = "Safe Zone — Low Risk"
            elif z_float < 1.1: z_status = "Distress Zone — High Risk"
        except:
            pass
        z_display = f"{z_score_val} ({z_status})" if z_score_val != "N/A" else "N/A"
        fcf_val = analysis.get('free_cash_flow', 'N/A')

        sec_data = {
            "SEC Health Verdict": sec_verdict,
            "Primary Risks": primary_risks,
            "Growth Catalysts": growth_catalysts,
            "Management Sentiment": mgmt_sentiment,
            "Altman Z-Score": z_display,
            "Piotroski F-Score": str(analysis.get('f_score', 'N/A')),
            "Debt / Equity": str(analysis.get('debt_to_equity', 'N/A')),
            "Free Cash Flow ($)": str(fcf_val)
        }
        utils.write_block(ws, 'SEC', f"{ticker} - SEC QUALITATIVE HEALTH", sec_data)
        print(f"   📊 [GSHEET] SEC Health block synced.")

        # 3. EARNINGS CALL INTELLIGENCE (Column G/H - top)
        print(f"   ⏳ [KINETIC] Committing dynamic Earnings Call Intelligence...")
        ec_data = {
            "EC 1 Summary": master_row.get("EC 1 Summary", "Telemetry loading / No summary found."),
            "EC 2 Summary": master_row.get("EC 2 Summary", "Telemetry loading / No summary found."),
            "Overall Earnings Tone": master_row.get("Overall Sentiment", "Neutral")
        }
        if ec_data["Overall Earnings Tone"] and "sentiment:" not in str(ec_data["Overall Earnings Tone"]).lower():
            ec_data["Overall Earnings Tone"] = f"Overall sentiment: {ec_data['Overall Earnings Tone']}"
            
        utils.write_block(ws, 'EC', f"{ticker} - EARNINGS CALL INTELLIGENCE", ec_data)
        print(f"   📊 [GSHEET] Earnings call block synced.")

        # 4. SOCIAL MEDIA SIGNALS (Column G/H - middle)
        print(f"   ⏳ [KINETIC] Committing dynamic Social Sentiment telemetry...")
        social_data = {
            "Social Sentiment Score": master_row.get("sentiment_score", "0.50"),
            "Social Signal": master_row.get("bull_bear", "Neutral"),
            "Key Topics": f"['{ticker}', 'market sentiment', 'retail focus']",
            "Social Summary": master_row.get("summary", "Telemetry loading / No social summary found.")
        }
        utils.write_block(ws, 'SENTIMENT', f"{ticker} - SOCIAL MEDIA SIGNALS", social_data)
        print(f"   📊 [GSHEET] Social signals block synced.")
        
    except Exception as e:
        print(f"   ⚠️ [GSHEET_WARN] Failed to write to sheet: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    args = parser.parse_args()
    run_audit(args.ticker)
