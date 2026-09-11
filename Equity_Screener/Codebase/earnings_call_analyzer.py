#!/usr/bin/env python3
"""
Earnings Call Analyzer for Alpha OS - Terminal Edition
Analyzes earnings call transcripts and populates Excel with comprehensive analysis

Usage:
    export ANTHROPIC_API_KEY="your-key-here"
    python earnings_call_analyzer.py input.xlsx [output.xlsx]
"""

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
import requests
import json
import os
from datetime import datetime
import time
import re
import sys

# Import components from local project
from nlp_analysis import AIService
from data_ingestion import DefeatBetaProvider

def get_api_key():
    """Get API key from environment or fallback to hardcoded NVIDIA key"""
    key = os.getenv('NVIDIA_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    return key  # May be None, AIService handles fallback

def search_and_analyze_earnings_call(ticker, company_name, api_key, max_retries=2):
    """
    Use DefeatBeta to find transcripts and NVIDIA NIM (Llama 3.1 8B) for analysis.
    """
    
    # 1. Fetch transcripts via DefeatBeta
    print(f"    🔍 Fetching transcripts for {ticker} via DefeatBeta...")
    try:
        provider = DefeatBetaProvider()
        research_data = provider.get_deep_research(ticker)
        transcripts = research_data.get('transcripts', [])
    except Exception as e:
        print(f"    ❌ Failed to fetch transcripts: {e}")
        return None

    if not transcripts:
        print(f"    ⚠️  No transcripts found for {ticker}")
        return {
            "transcript_url": "Not Found",
            "forward_guidance": "No recent earnings call available in database"
        }

    # 2. Analyze with NVIDIA NIM
    ai_service = AIService(api_key=api_key)
    
    transcript_text = "\n".join([f"Date: {t['date']}\nContent: {t['content'][:20000]}" for t in transcripts[:1]])
    
    prompt = f"""Analyze the most recent earnings call transcript for {company_name} ({ticker}).
    
    TRANSCRIPT:
    {transcript_text}

    Return analysis in this JSON format strictly:
    {{
      "transcript_url": "Institutional DB",
      "transcript_date": "{transcripts[0]['date']}",
      "forward_guidance": "Management outlook (max 200 chars)",
      "strategic_initiatives": "Key projects/products (max 150 chars)",
      "analyst_questions_themes": "Main themes from Q&A (max 150 chars)",
      "management_response_tone": "Description of tone (max 100 chars)",
      "beat_miss_vs_expectations": "Vs consensus (max 100 chars)",
      "margin_profitability": "Margin trends (max 100 chars)",
      "capex_investments": "CapEx plans (max 100 chars)",
      "competitive_positioning": "Vs competitors (max 100 chars)",
      "risk_flags": "Headwinds/risks (max 200 chars)",
      "key_takeaways": "Summary points (max 400 chars)",
      "overall_sentiment": "Bullish/Neutral/Bearish with reason (max 150 chars)"
    }}
    """

    print(f"    🧠 Analyzing with NVIDIA NIM (Llama 3.1 8B)...")
    for attempt in range(max_retries):
        try:
            # Use the underlying raw call logic or a general completion method
            # For simplicity, we'll re-implement the NIM call here or use ai_service.analyze_equity_qualitative
            # but that method has a different schema. Let's use a raw request logic similar to AIService.
            
            headers = {'Authorization': f'Bearer {ai_service.api_key}', 'Content-Type': 'application/json'}
            payload = {
                "model": ai_service.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2048
            }
            
            response = requests.post(ai_service.base_url, headers=headers, json=payload, timeout=300)
            
            if response.status_code == 200:
                text = response.json()['choices'][0]['message']['content']
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            elif response.status_code == 429:
                time.sleep(20)
                continue
            else:
                break
        except Exception as e:
            print(f"    ❌ Analysis error: {e}")
            time.sleep(5)
            
    return None
    
    return None  # All retries exhausted

def process_screening_excel(input_file, output_file, api_key):
    """Read screening Excel and add earnings call analysis"""
    
    print("\n" + "="*80)
    print("EARNINGS CALL ANALYZER")
    print("="*80)
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print("="*80 + "\n")
    
    # Read Excel - handle multi-sheet files
    try:
        excel_file = pd.ExcelFile(input_file)
        sheet_names = excel_file.sheet_names
        
        print(f"📑 Found {len(sheet_names)} sheets: {', '.join(sheet_names)}\n")
        
        # If multiple sheets, combine all non-summary sheets
        if len(sheet_names) > 1:
            all_dfs = []
            for sheet in sheet_names:
                if sheet.lower() == 'summary':
                    continue
                df_sheet = pd.read_excel(input_file, sheet_name=sheet)
                # Add sheet name as source
                df_sheet['Source_Sheet'] = sheet
                all_dfs.append(df_sheet)
            
            if not all_dfs:
                print("❌ No data sheets found (only Summary)\n")
                sys.exit(1)
            
            df = pd.concat(all_dfs, ignore_index=True)
            print(f"✅ Combined {len(all_dfs)} sector sheets\n")
        else:
            df = pd.read_excel(input_file)
        
    except Exception as e:
        print(f"❌ Failed to read {input_file}: {e}\n")
        sys.exit(1)
    
    print(f"📊 Found {len(df)} companies to analyze\n")
    
    # Find ticker column (try multiple variations)
    ticker_col = None
    for col in ['Ticker', 'ticker', 'TICKER', 'Symbol', 'symbol']:
        if col in df.columns:
            ticker_col = col
            break
    
    if not ticker_col:
        print(f"❌ Excel must have a ticker/symbol column")
        print(f"   Found columns: {df.columns.tolist()}\n")
        sys.exit(1)
    
    print(f"✅ Using '{ticker_col}' column for tickers\n")
    
    # Add earnings analysis columns (Matched to requested format)
    new_cols = [
        'EC 1 Summary',       # Strategic Initiatives / Business Updates
        'EC 2 Summary',       # Forward Guidance
        'EC 3 Summary',       # Key Takeaways & Competitors
        'EC 4 Summary',       # Risk Flags
        'Overall Sentiment'
    ]
    
    for col in new_cols:
        if col not in df.columns:
            df[col] = ''
    
    # Process each company
    success_count = 0
    not_found_count = 0
    failed_count = 0
    
    # Find company name column
    company_col = None
    for col in ['Company Name', 'company_name', 'Company', 'company', 'Name', 'name']:
        if col in df.columns:
            company_col = col
            break
    
    for idx, row in df.iterrows():
        ticker = str(row.get(ticker_col, '')).strip().upper()
        company_name = row.get(company_col, '') if company_col else ticker
        
        if not ticker:
            continue
        
        print(f"[{idx+1}/{len(df)}] {ticker} - {company_name}")
        
        # Run analysis
        analysis = search_and_analyze_earnings_call(ticker, company_name, api_key)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        if not analysis:
            print(f"    ❌ Analysis failed\n")
            df.at[idx, 'EC 1 Summary'] = 'Analysis Failed'
            failed_count += 1
            continue
        
        # Check if transcript found
        if analysis.get('transcript_url') == 'Not Found':
            print(f"    ⚠️  No transcript found\n")
            df.at[idx, 'EC 1 Summary'] = 'Not Found'
            df.at[idx, 'EC 2 Summary'] = analysis.get('forward_guidance', 'No transcript')
            not_found_count += 1
            continue
        
        # Populate all fields into EC 1-4 format
        # Combine related fields to create comprehensive summaries per block
        init = analysis.get('strategic_initiatives', '')
        takeaways = analysis.get('key_takeaways', '')
        pos = analysis.get('competitive_positioning', '')
        
        df.at[idx, 'EC 1 Summary'] = f"**Strategic Initiatives:**\n{init}"[:1500]
        df.at[idx, 'EC 2 Summary'] = f"**Forward Guidance & Margins:**\n{analysis.get('forward_guidance', '')}\n{analysis.get('margin_profitability', '')}"[:1500]
        df.at[idx, 'EC 3 Summary'] = f"**Key Takeaways & Positioning:**\n{takeaways}\n{pos}"[:1500]
        df.at[idx, 'EC 4 Summary'] = f"**Risk Flags:**\n{analysis.get('risk_flags', '')}"[:1500]
        df.at[idx, 'Overall Sentiment'] = analysis.get('overall_sentiment', '')[:500]
        
        sentiment = analysis.get('overall_sentiment', 'N/A')[:60]
        print(f"    ✅ {sentiment}")
        print(f"       {analysis.get('transcript_url', '')[:65]}...\n")
        
        success_count += 1
        
        # Rate limit - 20 second delay for Sonnet 4 (safest)
        time.sleep(20)
    
    # Save with formatting
    print("="*80)
    print("Saving results...")
    
    try:
        # If original file had multiple sheets, preserve them and add analysis sheet
        if len(sheet_names) > 1:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Copy original sheets
                for sheet in sheet_names:
                    original_df = pd.read_excel(input_file, sheet_name=sheet)
                    original_df.to_excel(writer, sheet_name=sheet, index=False)
                
                # Add new earnings analysis sheet
                df.to_excel(writer, index=False, sheet_name='Earnings Analysis')
                
                wb = writer.book
                ws = writer.sheets['Earnings Analysis']
                
                # Bloomberg terminal style header
                header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
                header_font = Font(bold=True, color='FFFFFF', size=10, name='Arial')
                
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                
                # Column widths (adjust based on number of columns)
                widths = {
                    'A': 10, 'B': 28, 'C': 18, 'D': 15, 'E': 12, 'F': 12,
                    'G': 45, 'H': 12, 'I': 45, 'J': 35, 'K': 35, 'L': 20,
                    'M': 25, 'N': 25, 'O': 25, 'P': 25, 'Q': 35, 'R': 50,
                    'S': 30, 'T': 16, 'U': 12, 'V': 12, 'W': 12, 'X': 12,
                    'Y': 12, 'Z': 12
                }
                
                for col, width in widths.items():
                    ws.column_dimensions[col].width = width
                
                # Format data rows
                data_font = Font(size=9, name='Arial')
                for row in ws.iter_rows(min_row=2):
                    for cell in row:
                        cell.alignment = Alignment(vertical='top', wrap_text=True)
                        cell.font = data_font
                
                # Freeze panes
                ws.freeze_panes = 'A2'
        else:
            # Single sheet file
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Earnings Analysis')
                
                wb = writer.book
                ws = writer.sheets['Earnings Analysis']
                
                # Bloomberg terminal style header
                header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
                header_font = Font(bold=True, color='FFFFFF', size=10, name='Arial')
                
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                
                # Column widths
                widths = {
                    'A': 10, 'B': 28, 'C': 18, 'D': 15, 'E': 12, 'F': 12,
                    'G': 45, 'H': 12, 'I': 45, 'J': 35, 'K': 35, 'L': 20,
                    'M': 25, 'N': 25, 'O': 25, 'P': 25, 'Q': 35, 'R': 50,
                    'S': 30, 'T': 16
                }
                
                for col, width in widths.items():
                    ws.column_dimensions[col].width = width
                
                # Format data rows
                data_font = Font(size=9, name='Arial')
                for row in ws.iter_rows(min_row=2):
                    for cell in row:
                        cell.alignment = Alignment(vertical='top', wrap_text=True)
                        cell.font = data_font
                
                # Freeze panes
                ws.freeze_panes = 'A2'
        
        print(f"✅ Saved: {output_file}")
        
    except Exception as e:
        print(f"❌ Save failed: {e}\n")
        sys.exit(1)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total companies:       {len(df)}")
    print(f"✅ Analyzed:           {success_count}")
    print(f"⚠️  No transcript:      {not_found_count}")
    print(f"❌ Failed:             {failed_count}")
    print("="*80 + "\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python earnings_call_analyzer.py <input.xlsx> [output.xlsx]")
        print("\nExample:")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        print("  python earnings_call_analyzer.py screening_results.xlsx\n")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.xlsx', '_with_earnings.xlsx')
    
    if not os.path.exists(input_file):
        print(f"\n❌ File not found: {input_file}\n")
        sys.exit(1)
    
    api_key = get_api_key()
    process_screening_excel(input_file, output_file, api_key)
