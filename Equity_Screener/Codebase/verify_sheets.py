import os
import pandas as pd
from run_screener import ProductionScreener

def verify_institutional_sheets():
    print("🚀 Verifying Institutional Google Sheets Dashboard...")
    
    # Create a mock Excel file for upload test
    dummy_xlsx = "/tmp/MSFT_mock_dcf.xlsx"
    pd.DataFrame({'test': [1,2,3]}).to_excel(dummy_xlsx)
    
    # Create mock results
    mock_df = pd.DataFrame({
        'ticker': ['MSFT', 'NVDA', 'PATH'],
        'company_name': ['Microsoft', 'NVIDIA', 'UiPath'],
        'price': [400.0, 900.0, 20.0],
        'fair_price': [450.0, 850.0, 30.0],
        'dcf_upside': [0.125, -0.055, 0.50],
        'wacc': [0.10, 0.12, 0.15],
        'roic': [0.15, 0.20, 0.25],
        'qual_sentiment': [80, 90, 60],
        'sentiment_drift': ['improving', 'stable', 'improving'],
        'composite_score': [85, 88, 75],
        'ai_summary': ['Dominant AI position.', 'Supply constrained growth.', 'Focus on path to profitability.'],
        'market_cap': [3e12, 2.2e12, 1e10],
        'dcf_local_path': [dummy_xlsx, None, None]
    })
    
    results = {"Information Technology": mock_df}
    
    # Initialize Screener (Force deep research flags for link generation)
    screener = ProductionScreener(google_api_key=os.getenv('GOOGLE_API_KEY'))
    screener.google_folder_id = "1B6shb7SZXVu6D-SPTyoUm9VJoFAkQmK3"
    screener.google_creds = "client_secret.json"
    screener.deep_research = True 
    
    timestamp = "VERIFY_MODELS"
    
    print("\nAttempting export to Google Sheets + Model Upload...")
    try:
        screener._export_to_google_sheet(results, screener.google_folder_id, screener.google_creds, timestamp)
        print("\n✅ Verification SUCCESS: Export triggered. Check the 'Deep-Dive Model' column in Google Sheets.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Verification FAILED: {e}")

if __name__ == "__main__":
    verify_institutional_sheets()
