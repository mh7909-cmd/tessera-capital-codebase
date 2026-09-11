"""Constants and utilities related to analysts configuration."""

from src.agents import portfolio_manager
from src.agents.valuation_lead import valuation_lead_agent
from src.agents.deep_value_analyst import deep_value_analyst_agent
from src.agents.activist_analyst import activist_analyst_agent
from src.agents.disruptive_innovation_analyst import disruptive_innovation_analyst_agent
from src.agents.quality_investing_lead import quality_investing_lead_agent
from src.agents.fundamentals import fundamentals_analyst_agent
from src.agents.contrarian_analyst import contrarian_analyst_agent
from src.agents.qualitative_growth_analyst import qualitative_growth_analyst_agent
from src.agents.practical_growth_analyst import practical_growth_analyst_agent
from src.agents.sentiment import sentiment_analyst_agent
from src.agents.global_macro_lead import global_macro_lead_agent
from src.agents.technicals import technical_analyst_agent
from src.agents.valuation import valuation_analyst_agent
from src.agents.core_value_strategist import core_value_strategist_agent
from src.agents.emerging_market_analyst import emerging_market_analyst_agent
from src.agents.low_risk_value_analyst import low_risk_value_analyst_agent
from src.agents.news_sentiment import news_sentiment_agent
from src.agents.growth_agent import growth_analyst_agent
from src.agents.growth_investor_agent import secular_growth_analyst_agent
from src.agents.macro_agent import global_macro_analyst_agent

# Define analyst configuration - single source of truth
ANALYST_CONFIG = {
    "valuation_lead": {
        "display_name": "Intrinsic Valuation Lead",
        "description": "DCF and fundamental valuation specialist",
        "investing_style": "Focuses on intrinsic value and financial metrics to assess investment opportunities through rigorous valuation analysis.",
        "agent_func": valuation_lead_agent,
        "type": "analyst",
        "order": 0,
    },
    "deep_value_analyst": {
        "display_name": "Deep Value Analyst",
        "description": "Margin of safety and liquidation value specialist",
        "investing_style": "Emphasizes a margin of safety and invests in undervalued companies with strong fundamentals through systematic value analysis.",
        "agent_func": deep_value_analyst_agent,
        "type": "analyst",
        "order": 1,
    },
    "activist_analyst": {
        "display_name": "Activist Strategy Lead",
        "description": "Corporate governance and value unlocking specialist",
        "investing_style": "Seeks to influence management and unlock value through strategic activism and contrarian investment positions.",
        "agent_func": activist_analyst_agent,
        "type": "analyst",
        "order": 2,
    },
    "disruptive_innovation_analyst": {
        "display_name": "Disruptive Innovation Analyst",
        "description": "Exponential growth and technology specialist",
        "investing_style": "Focuses on disruptive innovation and growth, investing in companies that are leading technological advancements and market disruption.",
        "agent_func": disruptive_innovation_analyst_agent,
        "type": "analyst",
        "order": 3,
    },
    "quality_investing_lead": {
        "display_name": "Quality Investing Lead",
        "description": "Compounding and business moat specialist",
        "investing_style": "Advocates for value investing with a focus on quality businesses and long-term growth through rational decision-making.",
        "agent_func": quality_investing_lead_agent,
        "type": "analyst",
        "order": 4,
    },
    "contrarian_analyst": {
        "display_name": "Contrarian Alpha Analyst",
        "description": "Short-selling and market asymmetry specialist",
        "investing_style": "Makes contrarian bets, often shorting overvalued markets and investing in undervalued assets through deep fundamental analysis.",
        "agent_func": contrarian_analyst_agent,
        "type": "analyst",
        "order": 5,
    },
    "low_risk_value_analyst": {
        "display_name": "Low-Risk Value Analyst",
        "description": "Asymmetric risk-reward value specialist",
        "investing_style": "Focuses on value investing and long-term growth through fundamental analysis and a margin of safety.",
        "agent_func": low_risk_value_analyst_agent,
        "type": "analyst",
        "order": 6,
    },
    "practical_growth_analyst": {
        "display_name": "Practical Growth Analyst",
        "description": "Consumer business and PEG ratio specialist",
        "investing_style": "Invests in companies with understandable business models and strong growth potential using the 'buy what you know' strategy.",
        "agent_func": practical_growth_analyst_agent,
        "type": "analyst",
        "order": 6,
    },
    "qualitative_growth_analyst": {
        "display_name": "Qualitative Growth Analyst",
        "description": "Management quality and R&D specialist",
        "investing_style": "Emphasizes investing in companies with strong management and innovative products, focusing on long-term growth through scuttlebutt research.",
        "agent_func": qualitative_growth_analyst_agent,
        "type": "analyst",
        "order": 7,
    },
    "emerging_market_analyst": {
        "display_name": "Emerging Markets Analyst",
        "description": "High-growth developing economy specialist",
        "investing_style": "Leverages macroeconomic insights to invest in high-growth sectors, particularly within emerging markets and domestic opportunities.",
        "agent_func": emerging_market_analyst_agent,
        "type": "analyst",
        "order": 8,
    },
    "global_macro_lead": {
        "display_name": "Global Macro Lead",
        "description": "Top-down trend and currency specialist",
        "investing_style": "Focuses on macroeconomic trends, making large bets on currencies, commodities, and interest rates through top-down analysis.",
        "agent_func": global_macro_lead_agent,
        "type": "analyst",
        "order": 9,
    },
    "core_value_strategist": {
        "display_name": "Core Value Strategist",
        "description": "Long-term compounding and moat specialist",
        "investing_style": "Seeks companies with strong fundamentals and competitive advantages through value investing and long-term ownership.",
        "agent_func": core_value_strategist_agent,
        "type": "analyst",
        "order": 10,
    },
    "technical_analyst": {
        "display_name": "Technical Analyst",
        "description": "Chart Pattern Specialist",
        "investing_style": "Focuses on chart patterns and market trends to make investment decisions, often using technical indicators and price action analysis.",
        "agent_func": technical_analyst_agent,
        "type": "analyst",
        "order": 11,
    },
    "fundamentals_analyst": {
        "display_name": "Fundamentals Analyst",
        "description": "Financial Statement Specialist",
        "investing_style": "Delves into financial statements and economic indicators to assess the intrinsic value of companies through fundamental analysis.",
        "agent_func": fundamentals_analyst_agent,
        "type": "analyst",
        "order": 12,
    },
    "growth_analyst": {
        "display_name": "Growth Analyst",
        "description": "Growth Specialist",
        "investing_style": "Analyzes growth trends and valuation to identify growth opportunities through growth analysis.",
        "agent_func": growth_analyst_agent,
        "type": "analyst",
        "order": 13,
    },
    "news_sentiment_analyst": {
        "display_name": "News Sentiment Analyst",
        "description": "News Sentiment Specialist",
        "investing_style": "Analyzes news sentiment to predict market movements and identify opportunities through news analysis.",
        "agent_func": news_sentiment_agent,
        "type": "analyst",
        "order": 14,
    },
    "sentiment_analyst": {
        "display_name": "Sentiment Analyst",
        "description": "Market Sentiment Specialist",
        "investing_style": "Gauges market sentiment and investor behavior to predict market movements and identify opportunities through behavioral analysis.",
        "agent_func": sentiment_analyst_agent,
        "type": "analyst",
        "order": 15,
    },
    "valuation_analyst": {
        "display_name": "Valuation Analyst",
        "description": "Company Valuation Specialist",
        "investing_style": "Specializes in determining the fair value of companies, using various valuation models and financial metrics for investment decisions.",
        "agent_func": valuation_analyst_agent,
        "type": "analyst",
        "order": 16,
    },
    "secular_growth_analyst": {
        "display_name": "Secular Growth Analyst",
        "description": "Innovation-driven growth specialist",
        "investing_style": "TAM, disruption, revenue CAGR, R&D intensity, innovation proxies.",
        "agent_func": secular_growth_analyst_agent,
        "type": "analyst",
        "order": 17,
        "debate_only": False,
    },
    "global_macro_analyst": {
        "display_name": "Global Macro Analyst",
        "description": "Top-down macroeconomic force specialist",
        "investing_style": "Sector forces, rates sensitivity, FX, geopolitics, commodities.",
        "agent_func": global_macro_analyst_agent,
        "type": "analyst",
        "order": 18,
        "debate_only": False,
    },
}

# Derive ANALYST_ORDER from ANALYST_CONFIG for backwards compatibility
ANALYST_ORDER = [(config["display_name"], key) for key, config in sorted(ANALYST_CONFIG.items(), key=lambda x: x[1]["order"])]


def get_analyst_nodes():
    """Get the mapping of analyst keys to their (node_name, agent_func) tuples."""
    return {
        key: (f"{key}_agent", config["agent_func"])
        for key, config in ANALYST_CONFIG.items()
        if not config.get("debate_only", False)
    }


def get_agents_list():
    """Get the list of agents for API responses."""
    return [
        {
            "key": key,
            "display_name": config["display_name"],
            "description": config["description"],
            "investing_style": config["investing_style"],
            "order": config["order"]
        }
        for key, config in sorted(ANALYST_CONFIG.items(), key=lambda x: x[1]["order"])
    ]
