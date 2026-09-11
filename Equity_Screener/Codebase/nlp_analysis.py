"""
NLP Analysis Module
Performs qualitative analysis on earnings transcripts, SEC filings, and news.
"""

import re
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque
from datetime import datetime
import json
import os
import requests
import time
import threading

class SimpleRateLimiter:
    """
    Thread-safe RPM limiter using a sliding window.
    """
    def __init__(self, requests_per_minute: int = 40):
        self.limit = requests_per_minute
        self.history = deque()
        self.lock = threading.Lock()

    def wait_for_slot(self):
        """Block until a request slot is available."""
        with self.lock:
            while True:
                now = time.monotonic()
                while self.history and self.history[0] <= now - 60:
                    self.history.popleft()
                if len(self.history) < self.limit:
                    self.history.append(now)
                    return
                sleep_time = self.history[0] + 60.1 - now
                if sleep_time > 0:
                    print(f"  [AIService] Stabilizing for deep analysis. Waiting {sleep_time:.1f}s...")
                    time.sleep(sleep_time)

class AIService:
    """
    Service layer for interacting with Google's Gemma 4 (via NVIDIA NIM).
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.model_name = "meta/llama-3.1-8b-instruct" # 10x Faster than Gemma for 'Flash' experience
        self.limiter = SimpleRateLimiter(requests_per_minute=50) # Increased speed buffer
        
    def analyze_equity_qualitative(self, ticker: str, company_name: str, sector: str, 
                                   transcripts: List[Dict] = None, 
                                   insider_buying: bool = False,
                                   sec_text: str = '') -> Dict:
        """Deep qualitative analysis with SEC Context window."""
        if not self.api_key or self.api_key == "placeholder":
            return self._mock_analysis()
        
        transcript_context = "No recent Q&A sessions or SEC filings found."
        if transcripts:
            transcript_context = ""
            for i, t in enumerate(transcripts):
                label = "LATEST (Q4/FY)" if i == 0 else "PREVIOUS (Q3)"
                
                # Extract ONLY Q&A to drastically reduce token weight (as per user request)
                content = t['content']
                if 'Question-and-Answer Session' in content:
                    qa_snippet = content.split('Question-and-Answer Session', 1)[-1][:10000]
                elif 'Questions and Answers' in content:
                    qa_snippet = content.split('Questions and Answers', 1)[-1][:10000]
                else:
                    # Fallback to the final 10,000 characters which usually contains Q&A
                    qa_snippet = content[-10000:]
                    
                transcript_context += f"\n--- {label} Q&A SESSION & RELEVANT DILIGENCE (Date: {t['date']}) ---\n{qa_snippet}\n"

        if sec_text:
            transcript_context += f"\n--- LATEST SEC FILING (10-K/10-Q Excerpt) ---\n{sec_text}\n"

        insider_status = "POSITIVE: Recent buying detected" if insider_buying else "Neutral"
        prompt = f"""
        Act as a Lead Equity Research Analyst. Perform an exhaustive qualitative deep-dive for {company_name} ({ticker}).
        
        INPUT DATA:
        {transcript_context}
        
        Insider Sentiment: {insider_status}
        
        RESEARCH TASKS:
        1. Analyze management tone and confidence shifts.
        2. Identify hidden risks or analyst concerns.
        3. Rank non-obvious catalysts.
        
        Return ONLY valid JSON:
        {{
            "overall_sentiment": -100 to 100,
            "sentiment_drift": "improving/stable/deteriorating",
            "confidence_score": 0 to 100,
            "catalysts": ["list with brief evidence"],
            "risk_flags": ["list with brief evidence"],
            "summary": "Detailed institutional summary",
            "is_sandbagging": true/false,
            "sandbagging_evidence": "Direct quote or metric from text proving management is being overly conservative"
        }}
        """
        
        max_retries = 2
        retry_delay = 5 # Faster retries for smaller model
        print(f"  [AIService] Pondering Diligence for {ticker} (using Llama-3.1-8B Speed Mode)...")
        start_time = time.time()
        
        for attempt in range(max_retries + 1):
            self.limiter.wait_for_slot()
            try:
                headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
                payload = {"model": self.model_name, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 2048}
                
                # Reduced timeout to 60s since 8B should never take 300s
                response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    text = response.json()['choices'][0]['message']['content']
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                            elapsed = time.time() - start_time
                            print(f"  [AIService] Research complete for {ticker} in {elapsed:.1f}s.")
                            return data
                        except Exception:
                            pass
                    
                    print(f"  [AIService] Warning: AI returned non-JSON for {ticker}. Retrying...")
                    time.sleep(2) # Quick breather
                    continue
                elif response.status_code == 429:
                    print(f"  [AIService] Peak Capacity Reached. Backing off for {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else: break
            except Exception as e:
                print(f"  [AIService] Error for {ticker}: {e}")
                time.sleep(retry_delay)
        return self._mock_analysis()

    def _mock_analysis(self) -> Dict:
        return {"overall_sentiment": 0, "sentiment_drift": "stable", "confidence_score": 50, "catalysts": [], "risk_flags": [], "summary": "Full Context Bypass.", "is_sandbagging": False}

class TranscriptAnalyzer:
    """Analyzes earnings call transcripts for sentiment and key phrases."""
    def __init__(self):
        self.sentiment_score = 0
    def analyze(self, text: str) -> float:
        return 0.0

class AnomalyDetector:
    """Detects unusual patterns in fundamental data or sentiment."""
    def __init__(self):
        pass
    def detect(self, data: pd.DataFrame) -> List[Dict]:
        return []
