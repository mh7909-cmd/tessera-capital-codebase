import os
from dotenv import load_dotenv
from sheets_handler import SheetsHandler
from twitter_scraper import TwitterScraper
from reddit_scraper import RedditScraper
from analyzer import SentimentAnalyzer

load_dotenv()

def test_google():
    print("Testing Google Sheets...")
    try:
        sh = SheetsHandler()
        tickers = sh.get_all_tickers()
        print(f"SUCCESS: Google Sheets working. Found {len(tickers)} tickers.")
        return True
    except Exception as e:
        print(f"FAILED: Google Sheets failed: {e}")
        return False

def test_nvidia():
    print("Testing NVIDIA NIM...")
    try:
        az = SentimentAnalyzer()
        res = az.analyze_sentiment("AAPL", "Apple", ["Apple is great!"], ["Buying AAPL."])
        if res.get('bull_bear'):
            print(f"SUCCESS: NVIDIA NIM working. Result: {res['bull_bear']}")
            return True
        else:
            print(f"FAILED: NVIDIA NIM returned unexpected format.")
            return False
    except Exception as e:
        print(f"FAILED: NVIDIA NIM failed: {e}")
        return False

def test_reddit():
    print("Testing Reddit (YARS)...")
    try:
        rs = RedditScraper()
        res = rs.scrape_ticker("AAPL", limit=2)
        print(f"SUCCESS: Reddit working. Found {len(res)} posts.")
        return True
    except Exception as e:
        print(f"FAILED: Reddit failed: {e}")
        return False

def test_twitter():
    print("Testing Twitter (Scweet)...")
    try:
        ts = TwitterScraper()
        res = ts.scrape_ticker("AAPL", limit=2)
        print(f"SUCCESS: Twitter working. Found {len(res)} tweets.")
        return True
    except Exception as e:
        print(f"FAILED: Twitter failed: {e}")
        return False

if __name__ == "__main__":
    test_google()
    test_nvidia()
    test_reddit()
    test_twitter()
