from Scweet import Scweet
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

class TwitterScraper:
    def __init__(self):
        self.auth_token = os.getenv('TWITTER_AUTH_TOKEN')
        if not self.auth_token:
            print("Warning: TWITTER_AUTH_TOKEN not found in .env")
        
        # Scweet handles its own state/db
        try:
            self.scweet = Scweet(auth_token=self.auth_token)
        except Exception as e:
            print(f"Error initializing Scweet: {e}")
            self.scweet = None

    def scrape_ticker(self, ticker, name=None, limit=20):
        """Scrapes tweets related to a ticker or company name."""
        if not self.scweet:
            return []
            
        # Search query: $TICKER OR "Company Name"
        query = f"${ticker}"
        if name:
            query += f' OR "{name}"'
            
        print(f"Scraping Twitter for: {query}")
        try:
            # Scweet.search returns a list of dictionaries in the latest versions
            tweets = self.scweet.search(query, display_type='Latest', limit=limit)
            
            cleaned_tweets = []
            for t in tweets:
                content = t.get('content') or t.get('full_text') or t.get('text')
                if content:
                    cleaned_tweets.append(content)
                    
            return cleaned_tweets
        except Exception as e:
            print(f"Error scraping Twitter for {ticker}: {e}")
            return []

if __name__ == "__main__":
    scraper = TwitterScraper()
    # Test with a popular ticker
    results = scraper.scrape_ticker("NVDA", "NVIDIA", limit=5)
    print(f"Found {len(results)} tweets.")
    for i, t in enumerate(results):
        print(f"{i+1}: {t[:100]}...")
        if i > 5: break
