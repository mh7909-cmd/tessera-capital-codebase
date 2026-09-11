from langchain_core.messages import HumanMessage
from src.graph.state import AgentState, show_agent_reasoning
from src.utils.api_key import get_api_key_from_state
from src.utils.progress import progress
import json

from src.tools.api import get_financial_metrics
from src.utils.llm import call_llm
from src.agents.cot_schema import CotAgentStructuredOutput, COT_SYSTEM_SUFFIX, cot_to_analyst_payload


##### Fundamental Agent #####
def fundamentals_analyst_agent(state: AgentState, agent_id: str = "fundamentals_analyst_agent"):
    """Analyzes fundamental data and generates trading signals for multiple tickers."""
    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
    # Initialize fundamental analysis for each ticker
    fundamental_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Fetching financial metrics")

        # Get the financial metrics
        financial_metrics = get_financial_metrics(
            ticker=ticker,
            end_date=end_date,
            period="ttm",
            limit=10,
            api_key=api_key,
        )

        if not financial_metrics:
            progress.update_status(agent_id, ticker, "Failed: No financial metrics found")
            continue

        # Pull the most recent financial metrics
        metrics = financial_metrics[0]

        # Call LLM for fundamental analysis
        progress.update_status(agent_id, ticker, "LLM reasoning on fundamentals")
        
        template = [
            ("system", 
             """YOUR INVESTMENT PHILOSOPHY:
             1. Analyze businesses for sustainable competitive advantages and durable moats.
             2. Focus on capital allocation, return on invested capital, and secular growth drivers.
             3. Prioritize high-quality cash flows and clean balance sheets.

             ADAPTIVE INTELLIGENCE RULES (Institutional Priority):
             1. Prioritize 'research_context' over external API data.
             2. If 'research_context' contradicts API metrics, favor the research.
             3. If API metrics are 'Insufficient data', use the documents to synthesize an opinion.
             """
             + COT_SYSTEM_SUFFIX
             + '\nUse "agent": "fundamentals_analyst".'),
            ("human", 
             f"Ticker: {ticker}\n"
             f"Metrics: {json.dumps(metrics.model_dump(), indent=2)}\n"
             f"Institutional Research Context: {data.get('research_context', 'N/A')}\n"
             "Perform an institutional-grade deep analysis of profitability, growth, financial health, and moat.")
        ]
        
        result = call_llm(
            model_name=state["metadata"]["model_name"],
            model_provider=state["metadata"]["model_provider"],
            system_prompt=template[0][1],
            messages=[template[1]],
            response_model=CotAgentStructuredOutput
        )
        
        fundamental_analysis[ticker] = cot_to_analyst_payload(result)
        progress.update_status(agent_id, ticker, "Done", analysis=result.conviction_reason)


        progress.update_status(agent_id, ticker, "Done", analysis=result.conviction_reason)


    # Create the fundamental analysis message
    message = HumanMessage(
        content=json.dumps(fundamental_analysis),
        name=agent_id,
    )

    # Print the reasoning if the flag is set
    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(fundamental_analysis, "Fundamental Analysis Agent")

    # Add the signal to the analyst_signals list
    state["data"]["analyst_signals"][agent_id] = fundamental_analysis

    
    return {
        "messages": [message],
        "data": data,
    }
