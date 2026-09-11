"""
NLP Analysis Module
Performs qualitative analysis on earnings transcripts, SEC filings, and news.
Detects sentiment shifts, management confidence, and information asymmetries.
"""

import re
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import Counter
from datetime import datetime
import json


class TranscriptAnalyzer:
    """
    Analyzes earnings call transcripts for sentiment and key phrases.
    """
    
    # Sector-specific keyword dictionaries
    SECTOR_KEYWORDS = {
        "Information Technology": {
            "positive": ["customer wins", "pipeline acceleration", "product-market fit", 
                        "adoption", "retention", "upsell", "expansion", "platform", "ecosystem"],
            "negative": ["churn", "competition", "pricing pressure", "dilution", "delays"],
            "catalysts": ["new product", "platform launch", "partnership", "integration"]
        },
        "Financials": {
            "positive": ["credit quality", "stable deposits", "core deposits", "diversified",
                        "net interest margin", "fee income", "cross-sell"],
            "negative": ["non-performing", "charge-offs", "provisions", "deposit flight"],
            "catalysts": ["rate sensitivity", "loan growth", "capital return"]
        },
        "Health Care": {
            "positive": ["trial success", "enrollment complete", "FDA approval", "reimbursement",
                        "market access", "commercial execution"],
            "negative": ["adverse events", "enrollment delays", "pricing pressure", "formulary"],
            "catalysts": ["readout", "PDUFA", "launch", "label expansion"]
        },
        "Consumer Discretionary": {
            "positive": ["traffic", "conversion", "market share", "brand strength", "pricing power"],
            "negative": ["promotional", "inventory build", "markdown", "store closures"],
            "catalysts": ["new store format", "omnichannel", "loyalty program"]
        },
        "Industrials": {
            "positive": ["backlog", "book-to-bill", "pricing realization", "operating leverage",
                        "aftermarket", "installed base"],
            "negative": ["order cancellations", "input costs", "supply chain"],
            "catalysts": ["new platforms", "contract wins", "capacity expansion"]
        }
    }
    
    def __init__(self, sector: str):
        self.sector = sector
        self.keywords = self.SECTOR_KEYWORDS.get(sector, {"positive": [], "negative": [], "catalysts": []})
    
    def analyze_transcript(self, transcript_text: str, 
                          previous_transcript: Optional[str] = None) -> Dict:
        """
        Analyze earnings call transcript.
        
        Returns:
            Dict with sentiment scores, keyword frequencies, and change indicators
        """
        # Clean text
        text = self._clean_text(transcript_text)
        
        # Split into management remarks vs. Q&A
        mgmt_section, qa_section = self._split_sections(text)
        
        # Sentiment analysis
        sentiment = self._calculate_sentiment(text)
        mgmt_sentiment = self._calculate_sentiment(mgmt_section)
        qa_sentiment = self._calculate_sentiment(qa_section)
        
        # Keyword frequency
        keyword_freq = self._count_keywords(text)
        
        # Confidence indicators
        confidence_score = self._assess_confidence(mgmt_section)
        
        # Compare to previous quarter if available
        sentiment_change = None
        if previous_transcript:
            prev_sentiment = self._calculate_sentiment(previous_transcript)
            sentiment_change = sentiment - prev_sentiment
        
        return {
            'overall_sentiment': sentiment,
            'mgmt_sentiment': mgmt_sentiment,
            'qa_sentiment': qa_sentiment,
            'sentiment_change': sentiment_change,
            'confidence_score': confidence_score,
            'keyword_frequencies': keyword_freq,
            'positive_signals': self._extract_positive_signals(text),
            'negative_signals': self._extract_negative_signals(text),
            'catalyst_mentions': self._extract_catalysts(text)
        }
    
    def _clean_text(self, text: str) -> str:
        """Remove HTML tags, special characters, normalize whitespace."""
        # Remove HTML
        text = re.sub(r'<[^>]+>', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _split_sections(self, text: str) -> Tuple[str, str]:
        """
        Split transcript into management remarks and Q&A sections.
        Uses common section headers as markers.
        """
        # Common section markers
        qa_markers = [
            "question-and-answer",
            "q&a session",
            "questions and answers",
            "operator instructions"
        ]
        
        text_lower = text.lower()
        split_idx = len(text)
        
        for marker in qa_markers:
            idx = text_lower.find(marker)
            if idx != -1 and idx < split_idx:
                split_idx = idx
        
        mgmt_section = text[:split_idx]
        qa_section = text[split_idx:]
        
        return mgmt_section, qa_section
    
    def _calculate_sentiment(self, text: str) -> float:
        """
        Calculate sentiment score (-100 to +100).
        Simplified implementation - in production use BERT/FinBERT.
        """
        positive_words = ["strong", "growth", "increase", "positive", "improved", 
                         "exceeded", "beat", "accelerate", "momentum", "optimistic",
                         "confident", "robust", "solid", "outperform"]
        
        negative_words = ["weak", "decline", "decrease", "negative", "deteriorate",
                         "miss", "slowdown", "headwinds", "pressure", "cautious",
                         "challenging", "difficult", "uncertain", "disappointing"]
        
        text_lower = text.lower()
        words = text_lower.split()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0
        
        return ((positive_count - negative_count) / total) * 100
    
    def _count_keywords(self, text: str) -> Dict[str, int]:
        """Count occurrences of sector-specific keywords."""
        text_lower = text.lower()
        
        counts = {
            'positive': {},
            'negative': {},
            'catalysts': {}
        }
        
        for category in ['positive', 'negative', 'catalysts']:
            for keyword in self.keywords[category]:
                count = text_lower.count(keyword.lower())
                if count > 0:
                    counts[category][keyword] = count
        
        return counts
    
    def _assess_confidence(self, mgmt_text: str) -> float:
        """
        Assess management confidence based on language patterns.
        Returns score 0-100.
        """
        text_lower = mgmt_text.lower()
        
        # Confident language
        confident_phrases = [
            "we are confident", "we expect", "we believe", "we see",
            "clearly", "definitely", "certainly", "strongly"
        ]
        
        # Hedging language
        hedging_phrases = [
            "might", "maybe", "perhaps", "possibly", "could be",
            "uncertain", "unclear", "we'll see", "remains to be seen"
        ]
        
        confident_count = sum(text_lower.count(phrase) for phrase in confident_phrases)
        hedging_count = sum(text_lower.count(phrase) for phrase in hedging_phrases)
        
        if confident_count + hedging_count == 0:
            return 50  # Neutral
        
        confidence = (confident_count / (confident_count + hedging_count)) * 100
        return confidence
    
    def _extract_positive_signals(self, text: str) -> List[str]:
        """Extract sentences with positive signals."""
        sentences = self._split_sentences(text)
        positive_sentences = []
        
        for sentence in sentences:
            keyword_count = sum(
                sentence.lower().count(kw.lower()) 
                for kw in self.keywords['positive']
            )
            if keyword_count >= 2:  # At least 2 positive keywords
                positive_sentences.append(sentence.strip())
        
        return positive_sentences[:5]  # Top 5
    
    def _extract_negative_signals(self, text: str) -> List[str]:
        """Extract sentences with negative signals."""
        sentences = self._split_sentences(text)
        negative_sentences = []
        
        for sentence in sentences:
            keyword_count = sum(
                sentence.lower().count(kw.lower()) 
                for kw in self.keywords['negative']
            )
            if keyword_count >= 2:
                negative_sentences.append(sentence.strip())
        
        return negative_sentences[:5]
    
    def _extract_catalysts(self, text: str) -> List[str]:
        """Extract mentions of potential catalysts."""
        sentences = self._split_sentences(text)
        catalyst_sentences = []
        
        for sentence in sentences:
            keyword_count = sum(
                sentence.lower().count(kw.lower()) 
                for kw in self.keywords['catalysts']
            )
            if keyword_count >= 1:
                catalyst_sentences.append(sentence.strip())
        
        return catalyst_sentences[:5]
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]


class FilingAnalyzer:
    """
    Analyzes SEC filings (10-K, 10-Q) for risk factors and MD&A changes.
    """
    
    def __init__(self):
        pass
    
    def extract_risk_factors(self, filing_text: str) -> str:
        """Extract Risk Factors section from 10-K."""
        # Look for "Item 1A" which is Risk Factors
        pattern = r'Item\s+1A\.?\s+Risk Factors(.*?)Item\s+1B'
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group(1).strip()
        return ""
    
    def extract_mda(self, filing_text: str) -> str:
        """Extract MD&A section from 10-K/10-Q."""
        # Item 7 in 10-K, Item 2 in 10-Q
        pattern = r'Item\s+[27]\.?\s+Management.*?Discussion(.*?)Item\s+[78]'
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group(1).strip()
        return ""
    
    def compare_risk_factors(self, current_filing: str, previous_filing: str) -> Dict:
        """
        Compare risk factors between filings to detect new risks.
        """
        current_risks = self.extract_risk_factors(current_filing)
        previous_risks = self.extract_risk_factors(previous_filing)
        
        # Simple comparison - in production use sentence embeddings
        new_keywords = self._extract_new_keywords(current_risks, previous_risks)
        
        return {
            'new_risk_keywords': new_keywords,
            'risk_section_length_change': len(current_risks) - len(previous_risks)
        }
    
    def _extract_new_keywords(self, current: str, previous: str) -> List[str]:
        """Find keywords in current that weren't in previous."""
        # Simplified - just look for new significant words
        current_words = set(current.lower().split())
        previous_words = set(previous.lower().split())
        
        new_words = current_words - previous_words
        
        # Filter to meaningful words (length > 5, not common words)
        common_words = {'the', 'and', 'or', 'but', 'may', 'could', 'would', 'should'}
        significant_new = [
            w for w in new_words 
            if len(w) > 5 and w not in common_words
        ]
        
        return significant_new[:10]


class AnomalyDetector:
    """
    Detects divergences between management commentary and actual results.
    This is where alpha lives - finding what the market is missing.
    """
    
    def __init__(self):
        pass
    
    def detect_guidance_sandbagging(self, transcript: str, 
                                   actual_results: Dict,
                                   guidance: Dict) -> Dict:
        """
        Detect if management is sandbagging guidance.
        
        Signals:
        - Confident language in transcript vs. conservative guidance
        - Guidance below historical beat rates
        - Commentary suggesting better trends than guidance implies
        """
        analyzer = TranscriptAnalyzer("General")
        analysis = analyzer.analyze_transcript(transcript)
        
        # Check if confidence is high but guidance is conservative
        confidence = analysis['confidence_score']
        sentiment = analysis['overall_sentiment']
        
        # Compare guidance to consensus
        guidance_gap = None
        if guidance.get('revenue') and actual_results.get('consensus_revenue'):
            guidance_gap = (guidance['revenue'] - actual_results['consensus_revenue']) / actual_results['consensus_revenue']
        
        is_sandbagging = False
        if confidence > 70 and sentiment > 50 and guidance_gap and guidance_gap < -0.05:
            is_sandbagging = True
        
        return {
            'is_sandbagging': is_sandbagging,
            'confidence_score': confidence,
            'sentiment_score': sentiment,
            'guidance_vs_consensus': guidance_gap
        }
    
    def detect_margin_inflection(self, transcript: str,
                                historical_margins: List[float]) -> Dict:
        """
        Detect margin expansion commentary not yet in models.
        """
        # Look for margin-related keywords
        margin_keywords = [
            "efficiency", "automation", "price realization", "operating leverage",
            "cost savings", "productivity", "margin expansion"
        ]
        
        text_lower = transcript.lower()
        margin_mentions = sum(text_lower.count(kw) for kw in margin_keywords)
        
        # Check if margin mentions are increasing
        is_inflection = margin_mentions >= 5  # At least 5 mentions
        
        return {
            'margin_keyword_count': margin_mentions,
            'potential_inflection': is_inflection,
            'recent_margin_trend': self._calculate_trend(historical_margins)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate if trend is improving, stable, or declining."""
        if len(values) < 2:
            return "insufficient_data"
        
        recent_avg = np.mean(values[-2:])
        historical_avg = np.mean(values[:-2]) if len(values) > 2 else values[0]
        
        if recent_avg > historical_avg * 1.05:
            return "improving"
        elif recent_avg < historical_avg * 0.95:
            return "declining"
        else:
            return "stable"


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example transcript analysis
    example_transcript = """
    Thank you for joining our Q4 earnings call. We're very pleased with our results this quarter.
    Revenue grew 18% year-over-year, exceeding our guidance range. We're seeing strong customer wins
    in our enterprise segment, with pipeline acceleration across all regions. 
    
    Our product-market fit continues to improve, and we're confident in our ability to maintain 
    this momentum into 2026. We're also seeing better retention rates and significant upsell 
    opportunities within our existing customer base.
    
    On margins, we're implementing new efficiency initiatives that should drive operating leverage
    over the coming quarters. While we're taking a conservative approach to guidance, we believe
    the fundamentals of our business are stronger than ever.
    
    Question-and-Answer Session:
    Q: Can you talk about competitive dynamics?
    A: We're not seeing any meaningful pricing pressure. Our differentiation is clear.
    
    Q: What about churn rates?
    A: Churn has actually improved this quarter, down 20 basis points sequentially.
    """
    
    print("Transcript Analysis Example")
    print("="*60)
    
    analyzer = TranscriptAnalyzer("Information Technology")
    results = analyzer.analyze_transcript(example_transcript)
    
    print(f"Overall Sentiment: {results['overall_sentiment']:.1f}")
    print(f"Management Confidence: {results['confidence_score']:.1f}")
    print(f"\nKeyword Frequencies:")
    print(json.dumps(results['keyword_frequencies'], indent=2))
    print(f"\nPositive Signals:")
    for signal in results['positive_signals']:
        print(f"  - {signal[:100]}...")
    
    # Example anomaly detection
    print("\n" + "="*60)
    print("Anomaly Detection Example")
    
    detector = AnomalyDetector()
    sandbagging_analysis = detector.detect_guidance_sandbagging(
        transcript=example_transcript,
        actual_results={'consensus_revenue': 100},
        guidance={'revenue': 92}  # 8% below consensus
    )
    
    print(f"Potential Sandbagging: {sandbagging_analysis['is_sandbagging']}")
    print(f"Guidance vs Consensus: {sandbagging_analysis['guidance_vs_consensus']:.1%}")
