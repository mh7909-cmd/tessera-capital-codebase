import os
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

class SentimentAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('NVIDIA_API_KEY')
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=self.api_key,
            timeout=20.0  # 20 second hard timeout so it gracefully fails instead of hanging forever
        )
        self.model = "meta/llama-3.1-8b-instruct"

    def analyze_sentiment(self, ticker, name, twitter_data, reddit_data):
        """Analyzes sentiment for a stock using NVIDIA NIM, with fallback for no data."""
        
        combined_text = "\n---\n".join(twitter_data + reddit_data)
        
        if not combined_text:
            # NO MEDIA FALLBACK: Use LLM to generate a reasonable synthetic market consensus
            prompt = f"""
            No live social media data was found for {name} ({ticker}) in the last 24 hours. 
            Provide a high-level 'Market Consensus' sentiment analysis based on general investment community outlook and recent trends for this company.
            
            Provide your analysis in the following JSON format:
            {{
                "sentiment_score": -1.0 to 1.0,
                "bull_bear": "Bullish", "Bearish", or "Neutral",
                "urgency": "Low",
                "topics": "General market consensus",
                "summary": "[SYNTHETIC CONSENSUS] 1-2 sentence overview of general market sentiment for this stock."
            }}
            Only return the JSON.
            """
        else:
            prompt = f"""
            Analyze the following social media posts about {name} ({ticker}). 
            Social Media Data:
            {combined_text[:6000]} # Truncate to avoid context limit
            
            Provide your analysis in the following JSON format:
            {{
                "sentiment_score": -1.0 to 1.0,
                "bull_bear": "Bullish", "Bearish", or "Neutral",
                "urgency": "High", "Medium", or "Low",
                "topics": "list of key topics and other mentioned tickers",
                "summary": "1-2 sentence overview of current sentiment and catalysts"
            }}
            Only return the JSON.
            """


        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial analyst specializing in social media sentiment analysis. IMPORTANT: Always return valid JSON. Do not include unescaped newlines in your strings; use '\\n' instead."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                top_p=0.7,
                max_tokens=512,
            )
            
            content = response.choices[0].message.content.strip()
            
            # --- ROBUST JSON EXTRACTION ---
            import re
            try:
                # 1. Regex to find the actual JSON block
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                
                # 2. Linearize: Remove true newlines which break strings, but keep spaces
                # This is safer than escaping \n everywhere
                lines = content.splitlines()
                content = " ".join([l.strip() for l in lines if l.strip()])
                
                return json.loads(content)
            except Exception as e:
                # Final fallback: strip markdown and try once more
                print(f"   ⚠️ Cleanup failed, trying raw parse: {e}")
                clean_content = content.replace('\\n', ' ').replace('\\r', ' ')
                return json.loads(clean_content)

        except Exception as e:
            print(f"Error during analysis for {ticker}: {e}")
            return {
                'sentiment_score': 0,
                'bull_bear': 'Error',
                'urgency': 'N/A',
                'topics': 'N/A',
                'summary': f'Analysis failed: {str(e)}'
            }

if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    # Test with mock data
    mock_twitter = ["Wait for the dip on $NVDA, long term bull.", "NVIDIA Blackwell chips are insane!"]
    mock_reddit = ["Inverse WSB, selling my NVDA calls.", "NVIDIA earnings are going to be huge."]
    result = analyzer.analyze_sentiment("NVDA", "NVIDIA", mock_twitter, mock_reddit)
    print(json.dumps(result, indent=2))
