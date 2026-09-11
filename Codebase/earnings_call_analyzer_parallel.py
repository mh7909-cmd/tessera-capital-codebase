#!/usr/bin/env python3
"""
Earnings Call Analyzer - PARALLEL VERSION
Processes multiple companies simultaneously to work around rate limits

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python earnings_call_analyzer_parallel.py input.xlsx [output.xlsx] [--workers 3]
"""

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
import requests
import json
import os
from datetime import datetime
import time
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

def get_api_key():
    """Get Anthropic API key from environment"""
    key = os.getenv('ANTHROPIC_API_KEY')
    if not key:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not set")
        print("\nSet it with:")
        print('  export ANTHROPIC_API_KEY="sk-ant-..."')
        print("\nOr run with:")
        print('  ANTHROPIC_API_KEY="sk-ant-..." python earnings_call_analyzer_parallel.py input.xlsx\n')
        sys.exit(1)
    return key

def search_and_analyze_earnings_call(ticker, company_name, api_key, worker_id=0):
    """Analyze single company's earnings call"""
    
    try:
        prompt = f"""Find and analyze the most recent earnings call transcript for {company_name} ({ticker}).

Steps:
1. Search for recent earnings call transcript
2. Read the full transcript  
3. Analyze comprehensively

Return analysis in this JSON format:

{{
  "transcript_url": "URL of transcript source",
  "transcript_date": "Date of earnings call",
  "forward_guidance": "Management outlook (max 200 chars)",
  "strategic_initiatives": "Key strategic moves (max 150 chars)",
  "analyst_questions_themes": "Main Q&A themes (max 150 chars)",
  "management_response_tone": "Tone assessment (max 100 chars)",
  "beat_miss_vs_expectations": "Beat/miss (max 100 chars)",
  "margin_profitability": "Margin commentary (max 100 chars)",
  "capex_investments": "Capex plans (max 100 chars)",
  "competitive_positioning": "Competitive position (max 100 chars)",
  "risk_flags": "Red flags (max 200 chars)",
  "key_takeaways": "Summary (max 400 chars)",
  "overall_sentiment": "Bullish/Neutral/Bearish with reason (max 150 chars)"
}}

If no transcript: {{"transcript_url": "Not Found", "forward_guidance": "No recent earnings call available"}}

Return ONLY valid JSON."""

        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-sonnet-4-20250514',  # Back to Sonnet
                'max_tokens': 4000,
                'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}],
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=120
        )
        
        if response.status_code == 429:
            print(f"[W{worker_id}] {ticker} - Rate limited, retrying in 30s...")
            time.sleep(30)
            return search_and_analyze_earnings_call(ticker, company_name, api_key, worker_id)
        
        if response.status_code != 200:
            print(f"[W{worker_id}] {ticker} - API error {response.status_code}")
            return None
        
        result = response.json()
        
        # Extract text
        full_text = ""
        for block in result.get('content', []):
            if block.get('type') == 'text':
                full_text += block.get('text', '')
        
        if not full_text:
            return None
        
        # Parse JSON
        clean_text = full_text.strip()
        if clean_text.startswith('```'):
            clean_text = re.sub(r'^```(?:json)?\s*', '', clean_text)
            clean_text = re.sub(r'```\s*$', '', clean_text)
        
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', clean_text, re.DOTALL)
        if not json_match:
            return None
        
        return json.loads(json_match.group())
        
    except Exception as e:
        print(f"[W{worker_id}] {ticker} - Error: {str(e)}")
        return None

def analyze_company(args):
    """Worker function for parallel processing"""
    idx, row, ticker_col, company_col, api_key, worker_id = args
    
    ticker = str(row.get(ticker_col, '')).strip().upper()
    company_name = row.get(company_col, '') if company_col else ticker
    
    if not ticker:
        return idx, None
    
    print(f"[W{worker_id}] Starting: {ticker} - {company_name}")
    
    analysis = search_and_analyze_earnings_call(ticker, company_name, api_key, worker_id)
    
    if not analysis:
        print(f"[W{worker_id}] ❌ {ticker} - Failed")
        return idx, None
    
    if analysis.get('transcript_url') == 'Not Found':
        print(f"[W{worker_id}] ⚠️  {ticker} - No transcript")
    else:
        sentiment = analysis.get('overall_sentiment', 'N/A')[:40]
        print(f"[W{worker_id}] ✅ {ticker} - {sentiment}")
    
    return idx, analysis

def process_screening_excel_parallel(input_file, output_file, api_key, num_workers=3):
    """Process screening Excel with parallel workers"""
    
    print("\n" + "="*80)
    print("EARNINGS CALL ANALYZER - PARALLEL MODE")
    print("="*80)
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print(f"Workers: {num_workers}")
    print("="*80 + "\n")
    
    # Read Excel
    try:
        excel_file = pd.ExcelFile(input_file)
        sheet_names = excel_file.sheet_names
        
        print(f"📑 Found {len(sheet_names)} sheets\n")
        
        # Combine non-summary sheets
        if len(sheet_names) > 1:
            all_dfs = []
            for sheet in sheet_names:
                if sheet.lower() == 'summary':
                    continue
                df_sheet = pd.read_excel(input_file, sheet_name=sheet)
                df_sheet['Source_Sheet'] = sheet
                all_dfs.append(df_sheet)
            
            if not all_dfs:
                print("❌ No data sheets found\n")
                sys.exit(1)
            
            df = pd.concat(all_dfs, ignore_index=True)
        else:
            df = pd.read_excel(input_file)
        
    except Exception as e:
        print(f"❌ Failed to read: {e}\n")
        sys.exit(1)
    
    print(f"📊 Found {len(df)} companies\n")
    
    # Find ticker column
    ticker_col = None
    for col in ['Ticker', 'ticker', 'Symbol', 'symbol']:
        if col in df.columns:
            ticker_col = col
            break
    
    if not ticker_col:
        print(f"❌ No ticker column found\n")
        sys.exit(1)
    
    # Find company name column
    company_col = None
    for col in ['Company Name', 'company_name', 'Company', 'company']:
        if col in df.columns:
            company_col = col
            break
    
    # Add earnings columns
    new_cols = [
        'EC_Transcript_URL', 'EC_Date', 'EC_Forward_Guidance',
        'EC_Strategic_Initiatives', 'EC_Analyst_Questions', 'EC_Mgmt_Response_Tone',
        'EC_Beat_Miss', 'EC_Margin_Commentary', 'EC_Capex_Plans',
        'EC_Competitive_Position', 'EC_Risk_Flags', 'EC_Key_Takeaways',
        'EC_Overall_Sentiment', 'EC_Analysis_Timestamp'
    ]
    
    for col in new_cols:
        if col not in df.columns:
            df[col] = ''
    
    # Prepare work items
    work_items = [
        (idx, row, ticker_col, company_col, api_key, idx % num_workers)
        for idx, row in df.iterrows()
        if str(row.get(ticker_col, '')).strip()
    ]
    
    print(f"🚀 Processing {len(work_items)} companies with {num_workers} workers...\n")
    
    # Process in parallel
    start_time = time.time()
    success_count = 0
    not_found_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(analyze_company, item): item for item in work_items}
        
        for future in as_completed(futures):
            idx, analysis = future.result()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if not analysis:
                df.at[idx, 'EC_Transcript_URL'] = 'Analysis Failed'
                df.at[idx, 'EC_Analysis_Timestamp'] = timestamp
                failed_count += 1
                continue
            
            if analysis.get('transcript_url') == 'Not Found':
                df.at[idx, 'EC_Transcript_URL'] = 'Not Found'
                df.at[idx, 'EC_Forward_Guidance'] = analysis.get('forward_guidance', '')
                df.at[idx, 'EC_Analysis_Timestamp'] = timestamp
                not_found_count += 1
                continue
            
            # Populate fields
            df.at[idx, 'EC_Transcript_URL'] = analysis.get('transcript_url', '')[:500]
            df.at[idx, 'EC_Date'] = analysis.get('transcript_date', '')
            df.at[idx, 'EC_Forward_Guidance'] = analysis.get('forward_guidance', '')[:1000]
            df.at[idx, 'EC_Strategic_Initiatives'] = analysis.get('strategic_initiatives', '')[:500]
            df.at[idx, 'EC_Analyst_Questions'] = analysis.get('analyst_questions_themes', '')[:500]
            df.at[idx, 'EC_Mgmt_Response_Tone'] = analysis.get('management_response_tone', '')[:200]
            df.at[idx, 'EC_Beat_Miss'] = analysis.get('beat_miss_vs_expectations', '')[:300]
            df.at[idx, 'EC_Margin_Commentary'] = analysis.get('margin_profitability', '')[:300]
            df.at[idx, 'EC_Capex_Plans'] = analysis.get('capex_investments', '')[:300]
            df.at[idx, 'EC_Competitive_Position'] = analysis.get('competitive_positioning', '')[:300]
            df.at[idx, 'EC_Risk_Flags'] = analysis.get('risk_flags', '')[:500]
            df.at[idx, 'EC_Key_Takeaways'] = analysis.get('key_takeaways', '')[:800]
            df.at[idx, 'EC_Overall_Sentiment'] = analysis.get('overall_sentiment', '')[:200]
            df.at[idx, 'EC_Analysis_Timestamp'] = timestamp
            
            success_count += 1
    
    elapsed = time.time() - start_time
    
    # Save results
    print("\n" + "="*80)
    print("Saving results...")
    
    try:
        if len(sheet_names) > 1:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for sheet in sheet_names:
                    original = pd.read_excel(input_file, sheet_name=sheet)
                    original.to_excel(writer, sheet_name=sheet, index=False)
                
                df.to_excel(writer, sheet_name='Earnings Analysis', index=False)
                
                ws = writer.sheets['Earnings Analysis']
                
                # Format header
                header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
                header_font = Font(bold=True, color='FFFFFF', size=10, name='Arial')
                
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                
                ws.freeze_panes = 'A2'
        else:
            df.to_excel(output_file, index=False)
        
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
    print(f"⏱️  Time elapsed:       {elapsed/60:.1f} minutes")
    print(f"⚡ Speed:              {elapsed/len(work_items):.1f} sec/company")
    print("="*80 + "\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Input Excel file')
    parser.add_argument('output_file', nargs='?', help='Output Excel file')
    parser.add_argument('--workers', type=int, default=3, help='Number of parallel workers (default: 3)')
    
    args = parser.parse_args()
    
    input_file = args.input_file
    output_file = args.output_file or input_file.replace('.xlsx', '_with_earnings.xlsx')
    
    if not os.path.exists(input_file):
        print(f"\n❌ File not found: {input_file}\n")
        sys.exit(1)
    
    api_key = get_api_key()
    process_screening_excel_parallel(input_file, output_file, api_key, args.workers)
