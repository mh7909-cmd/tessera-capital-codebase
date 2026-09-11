#!/usr/bin/env python3
"""
Test AI Equity Screener Installation
Verifies all dependencies and AI API connectivity

Usage:
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
    """Test API key availability"""
    print("\n" + "="*60)
    print("Testing AI Configuration")
    print("="*60)
    
    # Check for keys (or rely on hardcoded fallback)
    from nlp_analysis import AIService
    service = AIService()
    
    if service.api_key and service.api_key != "placeholder":
        print(f"✅ API key available ({service.api_key[:12]}...)")
        return True
    else:
        print("❌ No API key found in nlp_analysis.py or environment")
        return False

def test_api_connectivity():
    """Test NVIDIA NIM API connection"""
    print("\n" + "="*60)
    print("Testing NVIDIA NIM Connectivity")
    print("="*60)
    
    try:
        import requests
        from nlp_analysis import AIService
        service = AIService()
        
        if not service.api_key:
            print("⚠️  Skipping (no API key)")
            return False
        
        # Simple API test for Gemma 4 via NVIDIA NIM
        response = requests.post(
            service.base_url,
            headers={
                'Authorization': f'Bearer {service.api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': service.model_name,
                'messages': [{'role': 'user', 'content': 'Hi'}],
                'max_tokens': 10
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ NVIDIA NIM ({service.model_name}) connection successful")
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
        print("\n✅ All tests passed! You're ready to run the pipeline.")
        print("\nQuick start:")
        print("  python run_full_pipeline.py")
        print("  python run_screener.py --data-source yfinance\n")
    else:
        print("\n❌ Some tests failed. Fix issues above before running analyzer.\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
