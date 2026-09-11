from src.graph.state import AgentState, show_agent_reasoning
from src.tools.api import get_financial_metrics, get_market_cap, search_line_items
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
import json
from src.utils.progress import progress
from src.utils.llm import call_llm
import math
from src.utils.api_key import get_api_key_from_state
from src.agents.cot_schema import CotAgentStructuredOutput, COT_SYSTEM_SUFFIX, cot_to_analyst_payload, default_cot


def deep_value_analyst_agent(state: AgentState, agent_id: str = "deep_value_analyst"):
    """
    Analyzes stocks using classic deep value-investing principles:
    1. Earnings stability over multiple years.
    2. Solid financial strength (low debt, adequate liquidity).
    3. Discount to intrinsic value (e.g. Graham Number or net-net).
    4. Adequate margin of safety.
    """
    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
    
    analysis_data = {}
    value_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Fetching financial metrics")
        metrics = get_financial_metrics(ticker, end_date, period="annual", limit=10, api_key=api_key)

        progress.update_status(agent_id, ticker, "Gathering financial line items")
        financial_line_items = search_line_items(ticker, ["earnings_per_share", "revenue", "net_income", "book_value_per_share", "total_assets", "total_liabilities", "current_assets", "current_liabilities", "dividends_and_other_cash_distributions", "outstanding_shares"], end_date, period="annual", limit=10, api_key=api_key)

        progress.update_status(agent_id, ticker, "Getting market cap")
        market_cap = get_market_cap(ticker, end_date, api_key=api_key)

        # Perform sub-analyses
        progress.update_status(agent_id, ticker, "Analyzing earnings stability")
        earnings_analysis = analyze_earnings_stability(metrics, financial_line_items)

        progress.update_status(agent_id, ticker, "Analyzing financial strength")
        strength_analysis = analyze_financial_strength(financial_line_items)

        progress.update_status(agent_id, ticker, "Analyzing deep value metrics")
        valuation_analysis = analyze_valuation_value(financial_line_items, market_cap)

        # Aggregate scoring
        total_score = earnings_analysis["score"] + strength_analysis["score"] + valuation_analysis["score"]
        max_possible_score = 15  # total possible from the three analysis functions

        # Map total_score to signal
        if total_score >= 0.7 * max_possible_score:
            signal = "bullish"
        elif total_score <= 0.3 * max_possible_score:
            signal = "bearish"
        else:
            signal = "neutral"

        analysis_data[ticker] = {
            "signal": signal,
            "score": total_score,
            "max_score": max_possible_score,
            "earnings_analysis": earnings_analysis,
            "strength_analysis": strength_analysis,
            "valuation_analysis": valuation_analysis,
            "research_context": state["data"].get("research_context", "No external documents provided."),
        }

        progress.update_status(agent_id, ticker, "Generating deep value analysis")
        value_output = generate_deep_value_output(
            ticker=ticker,
            analysis_data=analysis_data,
            state=state,
            agent_id=agent_id,
        )
 
        value_analysis[ticker] = cot_to_analyst_payload(value_output)

        progress.update_status(agent_id, ticker, "Done", analysis=value_output.conviction_reason)

    # Wrap results in a single message for the chain
    message = HumanMessage(content=json.dumps(value_analysis), name=agent_id)
 
    # Optionally display reasoning
    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(value_analysis, "Deep Value Analyst")
 
    # Store signals in the overall state
    state["data"]["analyst_signals"][agent_id] = value_analysis


    return {"messages": [message], "data": state["data"]}


def analyze_earnings_stability(metrics: list, financial_line_items: list) -> dict:
    """
    Seek at least several years of consistently positive earnings (ideally 5+).
    We'll check:
    1. Number of years with positive EPS.
    2. Growth in EPS from first to last period.
    """
    score = 0
    details = []

    if not metrics or not financial_line_items:
        return {"score": score, "details": "Insufficient data for earnings stability analysis"}

    eps_vals = []
    for item in financial_line_items:
        if item.earnings_per_share is not None:
            eps_vals.append(item.earnings_per_share)

    if len(eps_vals) < 2:
        details.append("Not enough multi-year EPS data.")
        return {"score": score, "details": "; ".join(details)}

    # 1. Consistently positive EPS
    positive_eps_years = sum(1 for e in eps_vals if e > 0)
    total_eps_years = len(eps_vals)
    if positive_eps_years == total_eps_years:
        score += 3
        details.append("EPS was positive in all available periods.")
    elif positive_eps_years >= (total_eps_years * 0.8):
        score += 2
        details.append("EPS was positive in most periods.")
    else:
        details.append("EPS was negative in multiple periods.")

    # 2. EPS growth from earliest to latest
    if eps_vals[0] > eps_vals[-1]:
        score += 1
        details.append("EPS grew from earliest to latest period.")
    else:
        details.append("EPS did not grow from earliest to latest period.")

    return {"score": score, "details": "; ".join(details)}


def analyze_financial_strength(financial_line_items: list) -> dict:
    """
    Analyze liquidity (current ratio >= 2), manageable debt,
    and dividend record (preferably some history of dividends).
    """
    score = 0
    details = []

    if not financial_line_items:
        return {"score": score, "details": "No data for financial strength analysis"}

    latest_item = financial_line_items[0]
    total_assets = latest_item.total_assets or 0
    total_liabilities = latest_item.total_liabilities or 0
    current_assets = latest_item.current_assets or 0
    current_liabilities = latest_item.current_liabilities or 0

    # 1. Current ratio
    if current_liabilities > 0:
        current_ratio = current_assets / current_liabilities
        if current_ratio >= 2.0:
            score += 2
            details.append(f"Current ratio = {current_ratio:.2f} (>=2.0: solid).")
        elif current_ratio >= 1.5:
            score += 1
            details.append(f"Current ratio = {current_ratio:.2f} (moderately strong).")
        else:
            details.append(f"Current ratio = {current_ratio:.2f} (<1.5: weaker liquidity).")
    else:
        details.append("Cannot compute current ratio (missing or zero current_liabilities).")

    # 2. Debt vs. Assets
    if total_assets > 0:
        debt_ratio = total_liabilities / total_assets
        if debt_ratio < 0.5:
            score += 2
            details.append(f"Debt ratio = {debt_ratio:.2f}, under 0.50 (conservative).")
        elif debt_ratio < 0.8:
            score += 1
            details.append(f"Debt ratio = {debt_ratio:.2f}, somewhat high but could be acceptable.")
        else:
            details.append(f"Debt ratio = {debt_ratio:.2f}, quite high by Graham standards.")
    else:
        details.append("Cannot compute debt ratio (missing total_assets).")

    # 3. Dividend track record
    div_periods = [item.dividends_and_other_cash_distributions for item in financial_line_items if item.dividends_and_other_cash_distributions is not None]
    if div_periods:
        # In many data feeds, dividend outflow is shown as a negative number
        # (money going out to shareholders). We'll consider any negative as 'paid a dividend'.
        div_paid_years = sum(1 for d in div_periods if d < 0)
        if div_paid_years > 0:
            # e.g. if at least half the periods had dividends
            if div_paid_years >= (len(div_periods) // 2 + 1):
                score += 1
                details.append("Company paid dividends in the majority of the reported years.")
            else:
                details.append("Company has some dividend payments, but not most years.")
        else:
            details.append("Company did not pay dividends in these periods.")
    else:
        details.append("No dividend data available to assess payout consistency.")

    return {"score": score, "details": "; ".join(details)}


def analyze_valuation_value(financial_line_items: list, market_cap: float) -> dict:
    """
    Core approach to valuation:
    1. Net-Net Check: (Current Assets - Total Liabilities) vs. Market Cap
    2. Asset Number: sqrt(22.5 * EPS * Book Value per Share)
    3. Compare per-share price to Asset Number => margin of safety
    """
    if not financial_line_items or not market_cap or market_cap <= 0:
        return {"score": 0, "details": "Insufficient data to perform valuation"}

    latest = financial_line_items[0]
    current_assets = latest.current_assets or 0
    total_liabilities = latest.total_liabilities or 0
    book_value_ps = latest.book_value_per_share or 0
    eps = latest.earnings_per_share or 0
    shares_outstanding = latest.outstanding_shares or 0

    details = []
    score = 0

    # 1. Net-Net Check
    #   NCAV = Current Assets - Total Liabilities
    #   If NCAV > Market Cap => historically a strong buy signal
    net_current_asset_value = current_assets - total_liabilities
    if net_current_asset_value > 0 and shares_outstanding > 0:
        net_current_asset_value_per_share = net_current_asset_value / shares_outstanding
        price_per_share = market_cap / shares_outstanding if shares_outstanding else 0

        details.append(f"Net Current Asset Value = {net_current_asset_value:,.2f}")
        details.append(f"NCAV Per Share = {net_current_asset_value_per_share:,.2f}")
        details.append(f"Price Per Share = {price_per_share:,.2f}")

        if net_current_asset_value > market_cap:
            score += 4  # Very strong Graham signal
        # 2. Asset Number (Value Benchmark)
        #   AssetNumber = sqrt(22.5 * EPS * BVPS).
        #   Compare the result to the current price_per_share
        #   If AssetNumber >> price, indicates undervaluation
        asset_number = None
        if eps > 0 and book_value_ps > 0:
            asset_number = math.sqrt(22.5 * eps * book_value_ps)
            details.append(f"Asset Number = {asset_number:.2f}")
        else:
            details.append("Unable to compute Asset Number (EPS or Book Value missing/<=0).")
 
        # 3. Margin of Safety relative to Asset Number
        if asset_number and shares_outstanding > 0:
            current_price = market_cap / shares_outstanding
            if current_price > 0:
                margin_of_safety = (asset_number - current_price) / current_price
                details.append(f"Margin of Safety (Asset Number) = {margin_of_safety:.2%}")
                if margin_of_safety > 0.5:
                    score += 3
                    details.append("Price is well below Asset Number (>=50% margin).")
                elif margin_of_safety > 0.2:
                    score += 1
                    details.append("Some margin of safety relative to Asset Number.")
                else:
                    details.append("Price close to or above Asset Number, low margin of safety.")
        else:
            details.append("Current price is zero or invalid; can't compute margin of safety.")
    # else: already appended details for missing graham_number

    return {"score": score, "details": "; ".join(details)}


def generate_deep_value_output(
    ticker: str,
    analysis_data: dict[str, any],
    state: AgentState,
    agent_id: str,
) -> CotAgentStructuredOutput:
    """
    Generates an investment decision using deep value principles:
    - Value emphasis, margin of safety, net-nets, conservative balance sheet, stable earnings.
    """

    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """YOUR INVESTMENT PHILOSOPHY:
                1. Insist on a margin of safety by buying below intrinsic value.
                2. Emphasize financial strength (low leverage, ample current assets).
                3. Prefer stable earnings over multiple years.
                4. Focus on proven metrics, avoiding speculative growth.

                ADAPTIVE INTELLIGENCE RULES (Institutional Priority):
                1. Prioritize 'research_context' over external API data.
                2. If 'research_context' contradicts API metrics, favor the research.
                3. If API metrics are 'Insufficient data', use the documents to synthesize an opinion.
                """
                + COT_SYSTEM_SUFFIX
                + '\nUse "agent": "deep_value_analyst".',
            ),
            (
                "human",
                """Based on the following analysis, create a deep-value investment signal.

            Analysis Data for {ticker}:
            {analysis_data}

            Respond with the JSON object only.
            """,
            ),
        ]
    )

    prompt = template.invoke({"analysis_data": json.dumps(analysis_data, indent=2), "ticker": ticker})

    return call_llm(
        prompt=prompt,
        pydantic_model=CotAgentStructuredOutput,
        agent_name=agent_id,
        state=state,
        default_factory=lambda: default_cot("deep_value_analyst"),
    )
