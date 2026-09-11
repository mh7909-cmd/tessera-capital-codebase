"""
Demo Script for AI Equity Screening Agent
Shows how the system works with sample data.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

# Import our modules
from equity_screener_agent import EquityScreenerAgent, ITSectorScreener, FinancialsSectorScreener
from nlp_analysis import TranscriptAnalyzer, AnomalyDetector


def generate_sample_universe(n_stocks: int = 100) -> pd.DataFrame:
    """
    Generate sample stock universe for demonstration.
    In production, this comes from CapIQ/Bloomberg.
    """
    
    np.random.seed(42)
    
    sectors = [
        "Information Technology",
        "Financials",
        "Health Care",
        "Consumer Discretionary",
        "Industrials"
    ]
    
    data = []
    for i in range(n_stocks):
        sector = np.random.choice(sectors)
        market_cap = np.random.uniform(1e9, 50e9)
        
        # Generate realistic metrics
        record = {
            'ticker': f'DEMO{i:03d}',
            'company_name': f'Demo Company {i}',
            'sector': sector,
            'market_cap': market_cap,
            'price': np.random.uniform(10, 500),
            
            # IT metrics
            'gross_margin': np.random.uniform(0.2, 0.8),
            'revenue_growth_decel': np.random.uniform(-0.1, 0.3),
            'customer_concentration': np.random.uniform(0.05, 0.4),
            
            # Financials metrics
            'rotce': np.random.uniform(0.05, 0.25),
            'price_to_tbv': np.random.uniform(0.5, 3.0),
            'npl_trend': np.random.uniform(-0.05, 0.15),
            
            # Health Care metrics
            'pipeline_score': np.random.uniform(0, 100),
            'patent_cliff_risk': np.random.uniform(0, 0.5),
            
            # General metrics
            'ev_to_sales': np.random.uniform(0.5, 10),
            'fcf_yield': np.random.uniform(-0.05, 0.15),
            'net_debt_to_ebitda': np.random.uniform(-1, 5)
        }
        
        data.append(record)
    
    return pd.DataFrame(data)


def demo_it_sector_screening():
    """Demonstrate IT sector screening process."""
    
    print("\n" + "="*80)
    print("DEMO 1: INFORMATION TECHNOLOGY SECTOR SCREENING")
    print("="*80)
    
    # Generate sample IT stocks
    universe = generate_sample_universe(50)
    it_universe = universe[universe['sector'] == 'Information Technology'].copy()
    
    print(f"\nStarting universe: {len(it_universe)} IT stocks")
    print(f"Market cap range: ${it_universe['market_cap'].min()/1e9:.1f}B - ${it_universe['market_cap'].max()/1e9:.1f}B")
    
    # Initialize screener
    screener = ITSectorScreener(it_universe)
    
    # Run screening
    results = screener.run_sector_funnel()
    
    print(f"\n✓ Screening complete: {len(results)} stocks selected")
    
    if len(results) > 0:
        print("\nTop candidates:")
        display_cols = ['ticker', 'company_name', 'market_cap', 'gross_margin', 'revenue_growth_decel']
        print(results[display_cols].head(10).to_string(index=False))
    
    return results


def demo_financials_sector_screening():
    """Demonstrate Financials sector screening process."""
    
    print("\n" + "="*80)
    print("DEMO 2: FINANCIALS SECTOR SCREENING")
    print("="*80)
    
    # Generate sample Financials stocks
    universe = generate_sample_universe(50)
    fin_universe = universe[universe['sector'] == 'Financials'].copy()
    
    print(f"\nStarting universe: {len(fin_universe)} Financials stocks")
    
    # Initialize screener
    screener = FinancialsSectorScreener(fin_universe)
    
    # Run screening
    results = screener.run_sector_funnel()
    
    print(f"\n✓ Screening complete: {len(results)} stocks selected")
    
    if len(results) > 0:
        print("\nTop candidates:")
        display_cols = ['ticker', 'company_name', 'market_cap', 'rotce', 'price_to_tbv']
        print(results[display_cols].head(10).to_string(index=False))
    
    return results


def demo_nlp_analysis():
    """Demonstrate NLP analysis on sample transcript."""
    
    print("\n" + "="*80)
    print("DEMO 3: NLP TRANSCRIPT ANALYSIS")
    print("="*80)
    
    # Sample earnings call transcript
    sample_transcript = """
    Good afternoon everyone, and thank you for joining our Q4 2025 earnings call.
    
    I'm pleased to report strong results this quarter. Revenue grew 22% year-over-year,
    exceeding our guidance range. We're seeing accelerating customer wins in our enterprise
    segment, with particular strength in financial services and healthcare verticals.
    
    Our product-market fit continues to improve. Net retention rate reached 118%, up from
    115% last quarter, driven by both expansion revenue and improved retention. We're very
    confident in our competitive positioning - our platform offers differentiation that
    competitors simply can't match.
    
    On the efficiency front, we're implementing new automation initiatives that should drive
    meaningful operating leverage over the next several quarters. While we're taking a 
    conservative approach to FY26 guidance, we believe the underlying fundamentals of our
    business are stronger than they've ever been.
    
    Looking ahead, we see three key catalysts: First, our new AI features launching in Q2
    should drive significant upsell opportunities. Second, we're expanding into three new
    international markets. Third, our partnership with Microsoft is progressing ahead of
    schedule and should start contributing to revenue in the second half.
    
    Question-and-Answer Session:
    
    Analyst: Can you talk about competitive dynamics and any pricing pressure you're seeing?
    
    Management: We're not seeing any meaningful pricing pressure. If anything, we've been
    able to push through modest price increases due to the value we deliver. Our win rates
    remain strong.
    
    Analyst: What about churn - are you seeing any deterioration?
    
    Management: Actually the opposite. Churn improved 30 basis points sequentially. When
    customers see the ROI from our platform, they expand, they don't leave.
    """
    
    # Analyze transcript
    analyzer = TranscriptAnalyzer("Information Technology")
    analysis = analyzer.analyze_transcript(sample_transcript)
    
    print("\nTranscript Analysis Results:")
    print("-" * 60)
    print(f"Overall Sentiment Score:      {analysis['overall_sentiment']:>6.1f}")
    print(f"Management Sentiment:          {analysis['mgmt_sentiment']:>6.1f}")
    print(f"Q&A Sentiment:                 {analysis['qa_sentiment']:>6.1f}")
    print(f"Management Confidence:         {analysis['confidence_score']:>6.1f}%")
    
    print("\nKeyword Frequencies:")
    print("-" * 60)
    for category, keywords in analysis['keyword_frequencies'].items():
        if keywords:
            print(f"\n{category.upper()}:")
            for kw, count in sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  • {kw}: {count}x")
    
    print("\nPositive Signals Detected:")
    print("-" * 60)
    for i, signal in enumerate(analysis['positive_signals'][:3], 1):
        print(f"{i}. {signal[:100]}...")
    
    print("\nCatalyst Mentions:")
    print("-" * 60)
    for i, catalyst in enumerate(analysis['catalyst_mentions'][:3], 1):
        print(f"{i}. {catalyst[:100]}...")
    
    # Anomaly detection
    print("\n" + "="*80)
    print("Anomaly Detection: Guidance Sandbagging Analysis")
    print("="*80)
    
    detector = AnomalyDetector()
    sandbagging = detector.detect_guidance_sandbagging(
        transcript=sample_transcript,
        actual_results={'consensus_revenue': 100},
        guidance={'revenue': 95}  # 5% below consensus
    )
    
    print(f"\nPotential Sandbagging: {'YES' if sandbagging['is_sandbagging'] else 'NO'}")
    print(f"  Confidence Score:    {sandbagging['confidence_score']:.1f}%")
    print(f"  Sentiment Score:     {sandbagging['sentiment_score']:.1f}")
    print(f"  Guidance Gap:        {sandbagging['guidance_vs_consensus']:.1%} below consensus")
    
    if sandbagging['is_sandbagging']:
        print("\n⚠️  INVESTMENT THESIS:")
        print("     Management is highly confident (70%+ confidence score) but guiding")
        print("     conservatively. This creates potential for positive earnings surprises.")
        print("     Consider as long candidate pending further diligence.")


def demo_full_pipeline():
    """Demonstrate complete screening pipeline."""
    
    print("\n" + "="*80)
    print("DEMO 4: FULL PIPELINE - ALL SECTORS")
    print("="*80)
    
    # Generate larger universe
    universe = generate_sample_universe(200)
    
    print(f"\nGenerated universe: {len(universe)} stocks")
    print(f"Sectors: {universe['sector'].unique().tolist()}")
    print(f"Market cap range: ${universe['market_cap'].min()/1e9:.1f}B - ${universe['market_cap'].max()/1e9:.1f}B")
    
    # Initialize agent
    agent = EquityScreenerAgent(min_mcap=1e9, max_mcap=50e9)
    agent.universe = universe
    
    # Run full screening
    print("\nRunning sector-by-sector screening...")
    results = agent.run_full_screen()
    
    # Summary
    print("\n" + "="*80)
    print("SCREENING RESULTS SUMMARY")
    print("="*80)
    
    summary_data = []
    for sector, df in results.items():
        if len(df) > 0:
            summary_data.append({
                'Sector': sector,
                'Candidates': len(df),
                'Avg Mcap ($B)': f"{df['market_cap'].mean()/1e9:.1f}"
            })
    
    summary_df = pd.DataFrame(summary_data)
    print("\n" + summary_df.to_string(index=False))
    
    print(f"\n✓ Total candidates: {sum(len(df) for df in results.values())}")
    print(f"✓ Sectors screened: {len([s for s, df in results.items() if len(df) > 0])}")
    
    return results


def main():
    """Run all demos."""
    
    print("="*80)
    print("AI-NATIVE FUNDAMENTAL EQUITY SCREENING AGENT - DEMO")
    print("="*80)
    print(f"Demo Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis demo shows the system working with synthetic data.")
    print("In production, data comes from CapIQ, Bloomberg, or SEC EDGAR.")
    print("="*80)
    
    # Run demos
    try:
        # Demo 1: IT sector screening
        it_results = demo_it_sector_screening()
        
        # Demo 2: Financials sector screening  
        fin_results = demo_financials_sector_screening()
        
        # Demo 3: NLP analysis
        demo_nlp_analysis()
        
        # Demo 4: Full pipeline
        full_results = demo_full_pipeline()
        
        print("\n" + "="*80)
        print("DEMO COMPLETE")
        print("="*80)
        print("\nNext Steps:")
        print("  1. Connect to real data source (see README.md)")
        print("  2. Run: python run_screener.py --data-source yfinance")
        print("  3. Review output Excel files in /mnt/user-data/outputs/")
        print("  4. Build full models on top 10 candidates per sector")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Demo failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
