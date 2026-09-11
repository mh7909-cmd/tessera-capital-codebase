#!/usr/bin/env python3
"""
Alpha OS - Full Research Pipeline
Runs equity screening funnel → earnings call analysis

Usage:
    python run_full_pipeline.py [--industry INDUSTRY] [--skip-screening]
"""

import os
import sys
import subprocess
from datetime import datetime
import argparse

def run_screening(sector=None):
    """Run equity screening funnel"""
    print("\n" + "="*80)
    print("STEP 1: EQUITY SCREENING FUNNEL")
    print("="*80 + "\n")
    
    # Run your existing screener in unbuffered mode
    cmd = ['python', '-u', 'run_screener.py']
    if sector:
        cmd.extend(['--sector', sector])
    
    screening_file = None
    try:
        # Use Popen to stream output in real-time
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output line by line
        for line in process.stdout:
            print(line, end='')  # Print to terminal immediately
            
            # Extract output filename
            if 'equity_screen_' in line and '.xlsx' in line:
                import re
                match = re.search(r'equity_screen_\d+_\d+\.xlsx', line)
                if match:
                    screening_file = match.group()
        
        process.wait()
        
        if process.returncode != 0:
            print(f"❌ Screening failed with exit code {process.returncode}")
            return None
            
        # Fallback if filename wasn't captured in logs
        if not screening_file:
            import glob
            files = glob.glob('equity_screen_*.xlsx')
            if files:
                screening_file = max(files, key=os.path.getctime)
        
        return screening_file
        
    except Exception as e:
        print(f"❌ Error during screening: {e}")
        return None

def run_earnings_analysis(screening_file):
    """Run earnings call analyzer on screening output"""
    print("\n" + "="*80)
    print("STEP 2: EARNINGS CALL ANALYSIS")
    print("="*80 + "\n")
    
    output_file = screening_file.replace('.xlsx', '_with_earnings.xlsx')
    
    cmd = ['python', 'earnings_call_analyzer.py', screening_file, output_file]
    
    try:
        subprocess.run(cmd, check=True)
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"❌ Earnings analysis failed: {e}")
        return None

def run_google_sheets_upload(final_output):
    """Upload final output to Google Sheets"""
    cmd = ['python', 'upload_to_sheets.py', final_output]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Google Sheets upload failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run full Alpha OS research pipeline')
    parser.add_argument('--sector', type=str, help='Filter by sector (e.g. "Information Technology")')
    parser.add_argument('--skip-screening', action='store_true', 
                       help='Skip screening, use existing file')
    parser.add_argument('--screening-file', type=str,
                       help='Specific screening file to use (with --skip-screening)')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("ALPHA OS - FULL RESEARCH PIPELINE")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.sector:
        print(f"Sector Filter: {args.sector}")
    print("="*80)
    
    # Note: AIService uses hardcoded NVIDIA NIM key in nlp_analysis.py
    # No mandatory environment variable check required for Alpha OS v1.1
    
    # Step 1: Screening (or use existing)
    if args.skip_screening:
        if args.screening_file:
            screening_file = args.screening_file
        else:
            # Use most recent
            import glob
            files = glob.glob('equity_screen_*.xlsx')
            if not files:
                print("❌ No screening files found")
                sys.exit(1)
            screening_file = max(files, key=os.path.getctime)
        
        print(f"\n📊 Using existing screening: {screening_file}")
    else:
        screening_file = run_screening(args.sector)
        if not screening_file:
            print("\n❌ Pipeline failed at screening step")
            sys.exit(1)
    
    # Step 2: Earnings analysis
    final_output = run_earnings_analysis(screening_file)
    
    if not final_output:
        print("\n❌ Pipeline failed at earnings analysis step")
        sys.exit(1)
        
    # Step 3: Google Sheets Upload
    upload_success = run_google_sheets_upload(final_output)
    
    if not upload_success:
        print("\n⚠️ Pipeline completed, but Google Sheets upload failed. Data saved locally.")
    
    # Success
    print("\n" + "="*80)
    print("✅ PIPELINE COMPLETE")
    print("="*80)
    print(f"Final Output: {final_output}")
    print("\nNext steps:")
    if upload_success:
        print("  1. Open your Master Equity Screener in Google Sheets to review analysis")
    else:
        print("  1. Open the local Excel file to review analysis")
    print("  2. Filter by Overall Sentiment = 'Bullish'")
    print("  3. Review EC 4 Summary (Risk Flags) for red flags")
    print("  4. Begin primary research on high-conviction names")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
