#!/usr/bin/env python3
"""
Analyze Existing Screening Output
Quick script to run earnings analysis on your latest screening results

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python analyze_latest_screening.py
    
Or specify file:
    python analyze_latest_screening.py equity_screen_20260403_192718.xlsx
"""

import os
import sys
import glob
from datetime import datetime

def find_latest_screening():
    """Find most recent equity_screen_*.xlsx file"""
    files = glob.glob('equity_screen_*.xlsx')
    if not files:
        print("❌ No screening files found (looking for equity_screen_*.xlsx)")
        return None
    
    latest = max(files, key=os.path.getctime)
    return latest

def main():
    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("\n❌ ANTHROPIC_API_KEY not set")
        print("Set it with: export ANTHROPIC_API_KEY='sk-ant-...'\n")
        sys.exit(1)
    
    # Get file to analyze
    if len(sys.argv) > 1:
        screening_file = sys.argv[1]
    else:
        screening_file = find_latest_screening()
    
    if not screening_file:
        print("\nUsage: python analyze_latest_screening.py [screening_file.xlsx]\n")
        sys.exit(1)
    
    if not os.path.exists(screening_file):
        print(f"\n❌ File not found: {screening_file}\n")
        sys.exit(1)
    
    print(f"\n📊 Analyzing: {screening_file}\n")
    
    # Import and run analyzer
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from earnings_call_analyzer import process_screening_excel, get_api_key
        
        api_key = get_api_key()
        output_file = screening_file.replace('.xlsx', '_with_earnings.xlsx')
        
        process_screening_excel(screening_file, output_file, api_key)
        
    except ImportError:
        print("❌ earnings_call_analyzer.py not found in current directory")
        print("Make sure it's in the same folder as this script\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
