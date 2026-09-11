import os
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class ConvictionEngine:
    def __init__(self, state_path="thesis_state.json"):
        self.state_path = state_path
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.base_url = (os.getenv("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1") + "/chat/completions"
        self.model = "moonshotai/kimi-k2-thinking"
        self.thesis_state = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_path):
            with open(self.state_path, "r") as f:
                return json.load(f)
        return {}

    def _save_state(self):
        with open(self.state_path, "w") as f:
            json.dump(self.thesis_state, f, indent=4)

    def _clean_reasoning(self, raw: str) -> str:
        import re
        if not raw or raw == "N/A": return "N/A"
        text = re.sub(r'</?think>', '', raw, flags=re.IGNORECASE).strip()
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def evaluate_ticker(self, data: dict):
        ticker = data.get("ticker")
        company_name = data.get("company_name", ticker)
        
        # Load previous thesis
        previous_thesis = self.thesis_state.get(ticker, {})
        
        # WEIGHTING MATRIX
        weights = {
            "earnings_call": 0.9,
            "sec_filings": 0.9,
            "primary_research": 0.7,
            "supply_chain": 0.6,
            "social_sentiment": 0.3
        }

        prompt = f"""
        Perform a CONVICTION RE-EVALUATION on {company_name} ({ticker}).
        
        INPUT DATA:
        {json.dumps(data, indent=2)}
        
        PREVIOUS THESIS:
        {json.dumps(previous_thesis, indent=2) if previous_thesis else "No prior thesis exists."}
        
        WEIGHTING GUIDELINES:
        - Earnings Calls/SEC Filings: {weights['earnings_call']} impact
        - Supply Chain: {weights['supply_chain']} impact
        - Social Sentiment: {weights['social_sentiment']} impact

        TASKS:
        1. Identify CONTRADICTIONS: Look for new data that refutes the previous thesis.
        2. Assign WEIGHTED SCORES: Adjust conviction based on the source reliability weights above.
        3. Define PROBABILISTIC CONFIDENCE: Provide a range (e.g. 0.75-0.85) for the new conviction score.

        OUTPUT RAW JSON ONLY:
        {{
            "final_lean": "Long/Short/Neutral",
            "conviction_score": 0.0 to 1.0,
            "confidence_interval": [low, high],
            "strategic_rationale": "One-sentence rationale",
            "contradictions_found": ["list of specific conflicts"],
            "weighted_assumptions": [
                {{"assumption": "text", "weight": score, "status": "validated/disproven"}}
            ]
        }}
        """

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a hedge fund conviction engine. Output RAW JSON ONLY."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.05,
            "max_tokens": 4096
        }

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        print(f"🧠 Re-evaluating conviction for {ticker}...")
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=240)
            if response.status_code == 200:
                resp_json = response.json()
                content = resp_json["choices"][0]["message"]["content"]
                
                # Simple extraction
                import re
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    new_thesis = json.loads(match.group(0))
                    
                    # Update State
                    self.thesis_state[ticker] = {
                        **new_thesis,
                        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "reasoning_log": self._clean_reasoning(resp_json["choices"][0]["message"].get("reasoning", ""))
                    }
                    self._save_state()
                    print(f"✅ Conviction for {ticker}: {new_thesis.get('conviction_score')} ({new_thesis.get('final_lean')})")
                    return new_thesis
            else:
                print(f"❌ API Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Failure evaluating {ticker}: {e}")
        
        return None

if __name__ == "__main__":
    # Quick test loop
    engine = ConvictionEngine()
    # In a real run, this would be fed by your ingestion scripts
    mock_input = {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "data_sources": {
            "fundamentals": {"revenue_growth": 0.05, "debt_to_equity": 1.5},
            "sentiment": {"social_score": 0.8, "summary": "Bullish buzz about AI."},
            "earnings_calls": [{"period": "Q1 2026", "summary": "Strong services growth."}]
        }
    }
    engine.evaluate_ticker(mock_input)
