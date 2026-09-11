#!/usr/bin/env python3
"""
Alpha OS - Full Research Pipeline
Runs equity screening funnel → earnings call analysis

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python run_full_pipeline.py [--industry INDUSTRY] [--skip-screening]
"""

import os
import sys
import subprocess
from datetime import datetime
import argparse

def run_screening(industry=None):
    """Run equity screening funnel"""
    print("\n" + "="*80)
    print("STEP 1: EQUITY SCREENING FUNNEL")
    print("="*80 + "\n")
    
    # Run your existing screener
    cmd = ['python', 'run_screener.py']
    if industry:
        cmd.extend(['--industry', industry])
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        # Extract output filename from screener output
        # Assuming format like: equity_screen_YYYYMMDD_HHMMSS.xlsx
        for line in result.stdout.split('\n'):
            if 'equity_screen_' in line and '.xlsx' in line:
                # Extract filename
                import re
                match = re.search(r'equity_screen_\d+_\d+\.xlsx', line)
                if match:
                    return match.group()
        
        # Fallback - look for most recent equity_screen file
        import glob
        files = glob.glob('equity_screen_*.xlsx')
        if files:
            return max(files, key=os.path.getctime)
        
        print("⚠️  Could not find screening output file")
        return None
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Screening failed: {e}")
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

def main():
    parser = argparse.ArgumentParser(description='Run full Alpha OS research pipeline')
    parser.add_argument('--industry', type=str, help='Filter by industry')
    parser.add_argument('--skip-screening', action='store_true', 
                       help='Skip screening, use existing file')
    parser.add_argument('--screening-file', type=str,
                       help='Specific screening file to use (with --skip-screening)')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("ALPHA OS - FULL RESEARCH PIPELINE")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.industry:
        print(f"Industry Filter: {args.industry}")
    print("="*80)
    
    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("\n❌ ANTHROPIC_API_KEY not set")
        print("Set it with: export ANTHROPIC_API_KEY='sk-ant-...'\n")
        sys.exit(1)
    
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
        screening_file = run_screening(args.industry)
        if not screening_file:
            print("\n❌ Pipeline failed at screening step")
            sys.exit(1)
    
    # Step 2: Earnings analysis
    final_output = run_earnings_analysis(screening_file)
    
    if not final_output:
        print("\n❌ Pipeline failed at earnings analysis step")
        sys.exit(1)
    
    # Success
    print("\n" + "="*80)
    print("✅ PIPELINE COMPLETE")
    print("="*80)
    print(f"Final Output: {final_output}")
    print("\nNext steps:")
    print("  1. Open Excel file to review analysis")
    print("  2. Filter by EC_Overall_Sentiment = 'Bullish'")
    print("  3. Review EC_Risk_Flags for red flags")
    print("  4. Begin primary research on high-conviction names")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
