import datetime

def get_fly_metrics():
    """Mock financial metrics for FLY."""
    from src.data.models import FinancialMetrics
    return [
        FinancialMetrics(
            ticker="FLY",
            report_period="2024-03-31",
            period="ttm",
            currency="USD",
            market_cap=5380000000.0,
            enterprise_value=5820000000.0,
            price_to_earnings_ratio=None,
            price_to_book_ratio=4.5,
            price_to_sales_ratio=1.2,
            enterprise_value_to_ebitda_ratio=-24.8,
            enterprise_value_to_revenue_ratio=30.9,
            free_cash_flow_yield=-0.027,
            peg_ratio=None,
            revenue_growth=5.38,
            earnings_growth=-0.29,
            book_value_growth=0.12,
            ebitda_margin=-1.245,
            operating_margin=-1.24,
            net_profit_margin=-2.089,
            return_on_equity=-0.565,
            return_on_assets=-0.15,
            return_on_invested_capital=-0.22,
            current_ratio=4.51,
            debt_to_equity=25.93,
            debt_to_assets=0.67,
            quick_ratio=3.8,
            asset_turnover=0.15,
            inventory_turnover=None,
            receivables_turnover=12.5,
            revenue_per_share=5.38,
            net_income_per_share=-1.6,
            operating_cash_flow_per_share=-2.05,
            free_cash_flow_per_share=-1.46,
            cash_per_share=0.85,
            payout_ratio=0.0,
            earnings_per_share=-1.6,
            book_value_per_share=7.5
        )
    ]

def get_fly_line_items():
    """Mock line items for FLY."""
    from src.data.models import LineItem
    
    li_curr = LineItem(
        ticker="FLY",
        report_period="2024-03-31",
        period="ttm",
        currency="USD",
        revenue=538400000.0,
        cost_of_revenue=420000000.0,
        gross_profit=118400000.0,
        operating_income=-670000000.0,
        ebitda=-670000000.0,
        ebit=-670000000.0,
        net_income=-1124800000.0,
        total_assets=1200000000.0,
        total_liabilities=800000000.0,
        total_equity=400000000.0,
        operating_cash_flow=-204920000.0,
        capital_expenditure=150000000.0,
        free_cash_flow=-354920000.0,
        interest_expense=60000000.0,
        depreciation_and_amortization=35000000.0,
        outstanding_shares=100000000,
        working_capital=85000000.0,
        research_and_development=120000000.0,
        operating_expense=788400000.0
    )
    
    return [li_curr]

def get_fly_news():
    """Mock news for FLY."""
    from src.data.models import CompanyNews
    return [
        CompanyNews(
            ticker="FLY", 
            source="Internal Audit", 
            date="2024-03-15", 
            url="https://firefly.com/audit", 
            sentiment="negative", 
            title="Expert Report: Reaver engine reliability gap", 
            summary="Audit reveals ~69% stage reliability vs 95% requirement."
        ),
        CompanyNews(
            ticker="FLY", 
            source="Supply Chain Monitor", 
            date="2024-03-16", 
            url="https://firefly.com/supply", 
            sentiment="negative", 
            title="Helium supply crunch identified", 
            summary="Strategic supply limited to 2 launch manifest."
        ),
        CompanyNews(
            ticker="FLY", 
            source="Production Log", 
            date="2024-03-17", 
            url="https://firefly.com/production", 
            sentiment="negative", 
            title="Manufacturing Cadence Shortfall", 
            summary="Current production rate (18-24/yr) insufficient for 2026 targets (36/yr)."
        ),
        CompanyNews(
            ticker="FLY", 
            source="DoD Compliance", 
            date="2024-03-18", 
            url="https://firefly.com/dod", 
            sentiment="negative", 
            title="DoD Mission Success Thresholds Not Met", 
            summary="Internal audit flags structural reliability risks for upcoming orbital insertions."
        )
    ]

def get_fly_trades():
    """Mock insider trades for FLY."""
    from src.data.models import InsiderTrade
    return [
        InsiderTrade(
            ticker="FLY",
            transaction_date="2024-03-10",
            transaction_shares=-10000,
            transaction_price=35.0,
            transaction_value=-350000.0,
            insider_name="Mark Dankberg",
            insider_title="CEO",
            is_direct_ownership=True,
            filing_date="2024-03-12"
        )
    ]
