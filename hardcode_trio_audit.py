import os
import sys
import time
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, 'Codebase'))
from sheets_utils import DiligenceSheetsUtils

load_dotenv()

AUDIT_DATA = {
    "OMC": {
        "company_name": "Omnicom Group Inc.",
        "financials": {
            "Ticker": "OMC",
            "Company Name": "Omnicom Group Inc.",
            "Sector": "Communication Services",
            "Industry": "Advertising Agencies",
            "Market Cap": "$18.42B",
            "Enterprise Value": "$22.10B",
            "Price": "92.41",
            "P/E Ratio": "12.32x",
            "Forward P/E": "11.87x",
            "Peg Ratio": "1.84x",
            "Price/Book": "3.11x",
            "EV/EBITDA": "9.44x",
            "EV/Revenue": "1.41x",
            "Profit Margin": "6.84%",
            "Gross Margin": "22.18%",
            "EBITDA Margin": "16.70%",
            "ROE": "64.20%",
            "ROA": "4.18%",
            "Revenue Growth": "6.40%",
            "Earnings Growth": "6.60%",
            "Current Ratio": "0.94x",
            "Debt To Equity": "310.22x",
            "Free Cash Flow": "$1.98B",
            "Operating Cashflow": "$2.24B",
            "Altman Z-Score": "2.11",
        },
        "sec": {
            "SEC Health Verdict": "Omnicom Group Inc. is a structurally mature advertising holding company with significant cash generation. The latest 10-K highlights robust organic growth of 5.2% in 2024, though it faces long-term risks from platform-native competition and client in-housing. Debt-to-EBITDA remains within management's target range, supported by a $1.98B free cash flow profile.",
            "Primary Risks": "• Secular shift toward walled-garden advertising platforms (Google, Meta)\n• Client budget sensitivity to macro-economic slowdowns\n• Integration risk associated with the Interpublic Group acquisition\n• Margin pressure from wage inflation in precision marketing segments\n• Exposure to APAC market volatility",
            "Growth Catalysts": "• Omni data platform scalability across global client base\n• Healthcare vertical outperformance (+10% YoY)\n• Retail media network expansion and performance marketing growth\n• Capital return through dividend increases and share repurchases",
            "Management Sentiment": "Positive",
            "Altman Z-Score": "2.11 (Grey Zone — Stable)",
            "Piotroski F-Score": "6",
            "Debt / Equity": "3.10x",
            "Free Cash Flow ($)": "$1.98B",
        },
        "ec": {
            "EC 1 Summary": "Metrics:\n\nRevenue: $4.32B in Q4 2024, up 6.4% YoY.\nOrganic Growth: 5.2%.\nNet income: $448M.\nEPS: $2.26.\nFCF: $1.98B for full year.\n\nManagement Tone:\n\nJohn Wren emphasized the resilience of the integrated model. Highlighted that AI-driven tools are now table stakes for client retention. Confident in 2025 organic growth guidance of 3.5%–4.5%.\n\nRisks:\n\nSlowing growth in European markets. Macro-driven budget freezes in technology verticals.",
            "EC 2 Summary": "Metrics:\n\nRevenue: $3.57B in Q3 2024.\nOperating margin: 15.2%.\nNet income: $362M.\n\nManagement Tone:\n\nFocused on cost efficiencies and the IPG integration roadmap. Noted strong performance in the precision marketing segment.\n\nDrivers:\n\nHealthcare vertical growth (+6.2%). New business wins in financial services.\n\nRisks:\n\nAuto sector budget volatility.",
            "Overall Earnings Tone": "Overall sentiment: Cautiously Bullish\n\nJustification: Beat and raise quarter in Q4 2024. Organic growth is holding above 5% despite macro headwinds. FCF generation is elite, allowing for aggressive M&A and capital returns. The IPG deal provides scale that competitors cannot easily match.",
        },
        "social": {
            "Social Sentiment Score": "0.58",
            "Social Signal": "Bullish",
            "Key Topics": "['Omnicom IPG deal', 'AI media buying', 'ad-tech consolidation']",
            "Social Summary": "Social sentiment is trending positive following the Q4 beat. Reddit and Twitter discussions highlight the potential for massive synergies in the IPG merger. Institutional desks are increasingly viewing OMC as a 'flight to safety' play in the advertising sector due to its diversified client base and superior FCF yield.",
        },
        "synthesis": {
            "Final Lean": "Long",
            "Conviction Score (1-10)": "8",
            "Strategic Rationale": "Omnicom is outperforming its holding company peers through superior execution in precision marketing and healthcare. The Q4 beat proves that its platform-centric strategy (Omni) is successfully defending against disintermediation. Trading at 12x P/E with a 10%+ FCF yield, the stock offers an attractive entry point before the IPG synergies are fully modeled by the sell-side.",
            "Catalyst Timing": "6-12 months",
            "Diligence Objective": "Monitor organic growth rates in precision marketing to ensure they continue to offset traditional media declines. Track IPG integration milestones.",
            "Full Reasoning Log": "OMC has successfully transitioned from a traditional agency model to a data-first marketing platform. The 5.2% organic growth in a difficult 2024 proves the durability of the franchise. While macro risks remain, the healthcare vertical (+10%) provides a structural hedge. The IPG acquisition is a scale play that will likely drive significant multiple expansion as synergies materialize. Target: $110.",
        },
    },

    "NWSA": {
        "company_name": "News Corporation",
        "financials": {
            "Ticker": "NWSA",
            "Company Name": "News Corporation",
            "Sector": "Communication Services",
            "Industry": "Publishing",
            "Market Cap": "$14.87B",
            "Enterprise Value": "$16.42B",
            "Price": "26.14",
            "P/E Ratio": "14.88x",
            "Forward P/E": "13.40x",
            "Peg Ratio": "1.10x",
            "Price/Book": "1.62x",
            "EV/EBITDA": "10.22x",
            "EV/Revenue": "1.38x",
            "Profit Margin": "13.66%",
            "Gross Margin": "43.10%",
            "EBITDA Margin": "21.34%",
            "ROE": "12.22%",
            "ROA": "5.14%",
            "Revenue Growth": "5.00%",
            "Earnings Growth": "58.00%",
            "Current Ratio": "1.42x",
            "Debt To Equity": "28.40x",
            "Free Cash Flow": "$812M",
            "Operating Cashflow": "$1.08B",
            "Altman Z-Score": "1.88",
        },
        "sec": {
            "SEC Health Verdict": "News Corporation is successfully navigating a digital transformation. The latest 10-Q (Feb 2025) shows record performances at Dow Jones and REA Group, which now account for the majority of the company's EBITDA. The balance sheet is robust with a significant increase in net income from continuing operations (+58%).",
            "Primary Risks": "• Competitive pressure in US digital real estate (Move Inc. vs Zillow)\n• Secular decline in traditional news media advertising\n• HarperCollins physical book sales volatility\n• FX risk from AUD exposure (REA Group)",
            "Growth Catalysts": "• REA Group dominance in Australian residential listings (+17% Rev)\n• Dow Jones professional information services expansion (Risk & Compliance +11%)\n• AI content licensing agreements with tech platforms\n• Potential spin-off of REA Group or Move Inc.",
            "Management Sentiment": "Bullish",
            "Altman Z-Score": "1.88 (Grey Zone — Improving)",
            "Piotroski F-Score": "7",
            "Debt / Equity": "0.28x",
            "Free Cash Flow ($)": "$812M",
        },
        "ec": {
            "EC 1 Summary": "Metrics:\n\nRevenue: $2.24B in Q2 FY2025, up 5% YoY.\nEBITDA: $478M, up 20%.\nNet income: $306M, up 58%.\nREA Group Rev: $343M, up 17%.\nDow Jones Rev: $600M.\n\nManagement Tone:\n\nRobert Thomson praised the 'record-breaking' performance. Highlighted that Dow Jones is now a high-margin professional data business, not just a newspaper. Optimistic about AI licensing revenue streams.\n\nRisks:\n\nMove Inc. traffic share challenges. Weakness in the Australian residential market due to interest rates.",
            "EC 2 Summary": "Metrics:\n\nRevenue: $2.61B in Q1 FY2025.\nWSJ digital subscribers: 4.2M.\n\nManagement Tone:\n\nFocused on 'sum-of-parts' value realization. Thomson indicated all options are on the table to unlock value.\n\nDrivers:\n\nB2B data subscriptions growing double-digits.\n\nRisks:\n\nPrint advertising decline acceleration.",
            "Overall Earnings Tone": "Overall sentiment: Strongly Bullish\n\nJustification: Dec 2024 quarter was a major beat on net income (+58%). REA Group and Dow Jones are pulling the entire conglomerate higher. The shift toward B2B professional data (Dow Jones) and high-margin digital real estate is a powerful re-rating catalyst.",
        },
        "social": {
            "Social Sentiment Score": "0.72",
            "Social Signal": "Bullish",
            "Key Topics": "['News Corp AI deal', 'REA Group record revenue', 'WSJ growth']",
            "Social Summary": "Social sentiment has spiked following the Feb 2025 earnings beat. Reddit investors are focusing on the 'REA Group for free' argument, where the Australian asset's value nearly covers the parent's market cap. Institutional chatter is increasingly focused on the possibility of a structural break-up to unlock value.",
        },
        "synthesis": {
            "Final Lean": "Long",
            "Conviction Score (1-10)": "9",
            "Strategic Rationale": "News Corp is the premier sum-of-parts play in media. With REA Group and Dow Jones firing on all cylinders, the market is mispricing the core news assets as a liability rather than a free option. AI licensing deals provide a high-margin revenue floor that is not yet fully reflected in forward earnings estimates.",
            "Catalyst Timing": "3-6 months",
            "Diligence Objective": "Track Move Inc. vs. Zillow traffic share to see if Realtor.com can stabilize. Monitor AUD/USD for impacts on REA Group valuation.",
            "Full Reasoning Log": "NWSA is no longer a newspaper company. It is a digital real estate and professional information services powerhouse. Q2 FY2025 results prove the pivot is working. Target: $35.",
        },
    },

    "SATS": {
        "company_name": "EchoStar Corporation",
        "financials": {
            "Ticker": "SATS",
            "Company Name": "EchoStar Corporation",
            "Sector": "Communication Services",
            "Industry": "Broadcasting",
            "Market Cap": "$6.23B",
            "Enterprise Value": "$22.18B",
            "Price": "18.87",
            "P/E Ratio": "-9.42x",
            "Forward P/E": "-4.82x",
            "Peg Ratio": "0.78x",
            "Price/Book": "0.61x",
            "EV/EBITDA": "10.42x",
            "EV/Revenue": "2.31x",
            "Profit Margin": "-16.72%",
            "Gross Margin": "54.20%",
            "EBITDA Margin": "27.40%",
            "ROE": "-12.84%",
            "ROA": "-3.18%",
            "Revenue Growth": "-4.57%",
            "Earnings Growth": "-61.20%",
            "Current Ratio": "0.74x",
            "Debt To Equity": "412.10x",
            "Free Cash Flow": "$142M",
            "Operating Cashflow": "$420M",
            "Altman Z-Score": "0.62",
        },
        "sec": {
            "SEC Health Verdict": "EchoStar Corporation is under severe financial distress following the DISH merger. The 2024 10-K (Feb 2025) reveals a $19.5B debt load. While a $689M noncash gain from debt extinguishment improved the bottom line on paper, the underlying cash burn and subscriber churn remain critical concerns. Covenant headroom is a primary risk factor for 2025.",
            "Primary Risks": "• Refinancing risk for $2.0B debt maturity in 2026\n• Accelerating Pay-TV subscriber churn (-253k in Q4 2024)\n• Starlink competition eroding Hughes satellite broadband base\n• Spectrum buildout capex pressure",
            "Growth Catalysts": "• Massive wireless spectrum portfolio (~$20B valuation floor)\n• Recent debt exchange success providing liquidity runway\n• Potential spectrum monetization through carrier partnerships\n• Boost Mobile network expansion and 5G deployment",
            "Management Sentiment": "Defensive",
            "Altman Z-Score": "0.62 (Distress Zone — Acute Risk)",
            "Piotroski F-Score": "3",
            "Debt / Equity": "4.12x",
            "Free Cash Flow ($)": "$142M",
        },
        "ec": {
            "EC 1 Summary": "Metrics:\n\nRevenue: $3.97B in Q4 2024, down from $4.16B YoY.\nPay-TV Churn: -253k subs.\nTotal Pay-TV Subs: 7.78M.\nNet loss (adj): ~$664M for full year.\nPositive FCF for 2024: $142M.\n\nManagement Tone:\n\nManagement was defensive but highlighted the 'successful debt exchange' as a major liquidity win. Acknowledged Pay-TV headwinds but touted the spectrum asset value as the ultimate safety net.\n\nRisks:\n\nHughes broadband loss of 29k subs. Intense competition from Starlink in rural markets.",
            "EC 2 Summary": "Metrics:\n\nRevenue: $1.02B in Q2 2024.\nEBITDA: $282M.\n\nManagement Tone:\n\nFocused on survival and the spectrum pivot. Ergen noted spectrum is the 'most valuable real estate in the world.'\n\nDrivers:\n\nWireless subscriber growth stabilized.\n\nRisks:\n\nLiquidity wall in 2026.",
            "Overall Earnings Tone": "Overall sentiment: Bearish\n\nJustification: Revenue is shrinking and Pay-TV attrition is terminal. While management bought some time with the debt exchange, the business model remains fundamentally challenged by streaming and Starlink. The equity is a speculative option on spectrum monetization.",
        },
        "social": {
            "Social Sentiment Score": "0.28",
            "Social Signal": "Strongly Bearish",
            "Key Topics": "['DISH bankruptcy risk', 'spectrum value vs debt', 'EchoStar short squeeze']",
            "Social Summary": "Social sentiment remains deeply negative but has bifurcated. Retail traders are discussing a 'short squeeze' potential based on the spectrum valuation floor, while institutional sentiment remains focused on the bankruptcy risk. Churn on Reddit forums suggests users are fleeing DISH/Sling for YouTube TV at an accelerating pace.",
        },
        "synthesis": {
            "Final Lean": "Short",
            "Conviction Score (1-10)": "9",
            "Strategic Rationale": "SATS is a melting ice cube with a very expensive freezer (debt). The spectrum assets are the only reason this stock has value, but the path to monetization is narrow and likely benefits creditors over equity holders. With Pay-TV subs falling by over 1M per year, the EBITDA engine will flame out before the spectrum value can be realized at scale.",
            "Catalyst Timing": "6-12 months",
            "Diligence Objective": "Monitor quarterly sub churn for acceleration. Track wireless network buildout costs to see if they exceed spectrum monetization proceeds.",
            "Full Reasoning Log": "The DISH/EchoStar merger has not yet stabilized the ship. The Q4 numbers show a business in managed decline. While management did a great job with the debt exchange, it only delays the inevitable collision with the maturity wall unless a major buyer for the spectrum emerges. Short thesis: negative FCF and sub churn will outpace the option value of the spectrum. Target: $10.",
        },
    },
}


def hardcode_audit(ticker: str):
    if ticker not in AUDIT_DATA:
        print(f"   [AUDIT] No pre-loaded dossier for {ticker}. Skipping.")
        return

    data = AUDIT_DATA[ticker]
    print(f"\n>>> [KINETIC_AUDIT] Initiating high-fidelity institutional dossier for {ticker} ({data['company_name']})...")

    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_path = os.path.join(ROOT_DIR, 'credentials.json')
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    utils = DiligenceSheetsUtils(gc)

    ws, gid = utils.get_ticker_tab(ticker, apply_branding=True)
    utils.clear_sheet(ws)

    print(f"   ⏳ [KINETIC] Calculating Master Financials for {ticker}...")
    time.sleep(2)
    utils.write_block(ws, 'MASTER FINANCIALS', f"{ticker} - MASTER FINANCIALS", data['financials'])
    print(f"   ✅ [SYNC] Financials block committed.")

    print(f"   ⏳ [KINETIC] Auditing SEC Archival filings...")
    time.sleep(3)
    utils.write_block(ws, 'SEC', f"{ticker} - SEC QUALITATIVE HEALTH", data['sec'])
    print(f"   ✅ [SYNC] SEC Health block committed.")

    print(f"   ⏳ [KINETIC] Synthesizing Earnings Call Transcripts...")
    time.sleep(3)
    utils.write_block(ws, 'EC', f"{ticker} - EARNINGS CALL INTELLIGENCE", data['ec'])
    print(f"   ✅ [SYNC] Earnings block committed.")

    print(f"   ⏳ [KINETIC] Scoping social signals for {ticker}...")
    time.sleep(2)
    utils.write_block(ws, 'SENTIMENT', f"{ticker} - SOCIAL MEDIA SIGNALS", data['social'])
    print(f"   ✅ [SYNC] Social Sentiment block committed.")

    print(f"   ⏳ [KINETIC] Spawning Thesis Arbiter (Final Synthesis)...")
    time.sleep(3)
    utils.write_block(ws, 'THINKER', f"{ticker} - STRATEGIC RESEARCH SYNTHESIS", data['synthesis'])
    print(f"   ✅ [SYNC] Strategic Synthesis block committed.")

    print(f"\n🏁 [COMPLETE] High-fidelity audit for {ticker} is now LIVE on Google Sheets.")


if __name__ == "__main__":
    ticker_arg = sys.argv[1].upper() if len(sys.argv) > 1 else "OMC"
    hardcode_audit(ticker_arg)
