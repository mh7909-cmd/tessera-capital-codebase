from yars.yars import YARS
import os
import time

class RedditScraper:
    def __init__(self):
        # YARS is keyless
        self.miner = YARS()

    def scrape_ticker(self, ticker, name=None, limit=20):
        """Scrapes reddit posts related to a ticker or company name."""
        query = ticker
        if name:
            query = f"{ticker} {name}"
            
        print(f"Scraping Reddit for: {query}")
        
        try:
            # Search across all of reddit
            search_results = self.miner.search_reddit(query=query, limit=limit)
            
            cleaned_posts = []
            for res in search_results:
                title = res.get('title', '')
                desc = res.get('description', '')
                combined = f"{title}\n{desc}"
                cleaned_posts.append(combined)
            
            # Optional: Also search specific finance subreddits for better quality
            finance_subs = ['wallstreetbets', 'stocks', 'investing', 'options']
            for sub in finance_subs:
                sub_results = self.miner.search_subreddit(subreddit=sub, query=ticker, sort='new', limit=5)
                for res in sub_results:
                    title = res.get('title', '')
                    desc = res.get('description', '')
                    combined = f"{title}\n{desc}"
                    if combined not in cleaned_posts:
                        cleaned_posts.append(combined)
            
            return cleaned_posts
        except Exception as e:
            print(f"Error scraping Reddit for {ticker}: {e}")
            return []

if __name__ == "__main__":
    scraper = RedditScraper()
    results = scraper.scrape_ticker("NVDA", "NVIDIA", limit=5)
    print(f"Found {len(results)} reddit posts.")
    for i, t in enumerate(results):
        print(f"{i+1}: {t[:100]}...")
        if i > 5: break
