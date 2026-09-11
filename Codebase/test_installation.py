#!/usr/bin/env python3
"""
Test Earnings Call Analyzer Installation
Verifies all dependencies and API connectivity

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python test_installation.py
"""

import sys
import os

def test_imports():
    """Test required packages"""
    print("\n" + "="*60)
    print("Testing Package Dependencies")
    print("="*60)
    
    packages = {
        'pandas': 'pandas',
        'openpyxl': 'openpyxl',
        'requests': 'requests'
    }
    
    all_good = True
    for name, import_name in packages.items():
        try:
            __import__(import_name)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - Run: pip install {name}")
            all_good = False
    
    return all_good

def test_api_key():
    """Test API key is set"""
    print("\n" + "="*60)
    print("Testing API Configuration")
    print("="*60)
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        print("   Set with: export ANTHROPIC_API_KEY='sk-ant-...'")
        return False
    
    if not api_key.startswith('sk-ant-'):
        print("⚠️  API key doesn't start with 'sk-ant-'")
        print("   Make sure you're using an Anthropic API key")
        return False
    
    print(f"✅ API key set ({api_key[:12]}...)")
    return True

def test_api_connectivity():
    """Test API connection"""
    print("\n" + "="*60)
    print("Testing API Connectivity")
    print("="*60)
    
    try:
        import requests
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("⚠️  Skipping (no API key)")
            return False
        
        # Simple API test
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 100,
                'messages': [{'role': 'user', 'content': 'Hi'}]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ API connection successful")
            return True
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def test_analyzer_file():
    """Test analyzer script exists"""
    print("\n" + "="*60)
    print("Testing Analyzer Files")
    print("="*60)
    
    files = [
        'earnings_call_analyzer.py',
        'analyze_latest_screening.py',
        'QUICKSTART.md'
    ]
    
    all_good = True
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - Not found")
            all_good = False
    
    return all_good

def test_sample_data():
    """Test with sample data if available"""
    print("\n" + "="*60)
    print("Testing Sample Data")
    print("="*60)
    
    if os.path.exists('sample_screening_output.xlsx'):
        print("✅ Sample data found")
        print("   Run: python earnings_call_analyzer.py sample_screening_output.xlsx")
        return True
    else:
        print("ℹ️  No sample data found")
        print("   Download sample_screening_output.xlsx to test")
        return True  # Not a failure

def main():
    print("\n" + "="*60)
    print("EARNINGS CALL ANALYZER - INSTALLATION TEST")
    print("="*60)
    
    # Run tests
    results = {
        'Dependencies': test_imports(),
        'API Key': test_api_key(),
        'API Connection': test_api_connectivity(),
        'Analyzer Files': test_analyzer_file(),
        'Sample Data': test_sample_data()
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✅ All tests passed! You're ready to analyze earnings calls.")
        print("\nQuick start:")
        print("  python analyze_latest_screening.py")
        print("  python earnings_call_analyzer.py sample_screening_output.xlsx\n")
    else:
        print("\n❌ Some tests failed. Fix issues above before running analyzer.\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
