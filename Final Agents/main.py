import sys
import os

# Add the project root to sys.path so that 'src' can be imported correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from colorama import Fore, Style, init
import logging

# Institutional Silence: Suppress technical library noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
import questionary
from src.agents.portfolio_manager import portfolio_management_agent
from src.agents.risk_manager import risk_management_agent
from src.debate_orchestrator import debate_orchestrator_node
from src.agents.researcher import research_agent

from src.graph.state import AgentState
from src.utils.display import print_trading_output
from src.utils.report_gen import generate_thesis_report
from src.utils.trading import execute_alpaca_trade
from src.utils.analysts import ANALYST_ORDER, get_analyst_nodes
from src.utils.progress import progress
from src.utils.visualize import save_graph_as_png
from src.cli.input import (
    parse_cli_inputs,
)

import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json

# Load environment variables from .env file
load_dotenv()

init(autoreset=True)


def parse_hedge_fund_response(response):
    """Parses a JSON string and returns a dictionary."""
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}\nResponse: {repr(response)}")
        return None
    except TypeError as e:
        print(f"Invalid response type (expected string, got {type(response).__name__}): {e}")
        return None
    except Exception as e:
        print(f"Unexpected error while parsing response: {e}\nResponse: {repr(response)}")
        return None


##### Run the Hedge Fund #####
def run_hedge_fund(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    show_reasoning: bool = False,
    selected_analysts: list[str] = [],
    model_name: str = "gpt-4.1",
    model_provider: str = "OpenAI",
    use_debate: bool = False,
    company_name: str = None,
    pre_seeded_context: str = None,
):
    # Start progress tracking
    progress.start()

    try:
        # Build workflow (default to all analysts when none provided)
        workflow = create_workflow(
            selected_analysts if selected_analysts else None,
            use_debate=use_debate,
        )
        agent = workflow.compile()

        initial_data = {
            "tickers": tickers,
            "portfolio": portfolio,
            "start_date": start_date,
            "end_date": end_date,
            "analyst_signals": {},
        }
        # Pre-seed research context if a dossier was passed in
        # research_agent will PREPEND this to whatever it fetches from GSheets/GDrive
        if pre_seeded_context:
            initial_data["pre_seeded_context"] = pre_seeded_context
            print(f"[CONTEXT] Pre-seeded institutional dossier injected ({len(pre_seeded_context)} chars)")

        final_state = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Make trading decisions based on the provided data.",
                    )
                ],
                "data": initial_data,
                "metadata": {
                    "show_reasoning": show_reasoning,
                    "model_name": model_name,
                    "model_provider": model_provider,
                    "use_debate": use_debate,
                    "company_name": company_name,
                },
            },
        )

        out = {
            "decisions": parse_hedge_fund_response(final_state["messages"][-1].content),
            "analyst_signals": final_state["data"]["analyst_signals"],
        }
        if use_debate:
            out["debate_result"] = final_state["data"].get("debate_result", {})
            out["meta_agent_output"] = final_state["data"].get("meta_agent_output", {})
        
        # Add the final state to results for report generation
        out["state"] = final_state
        return out
    finally:
        # Stop progress tracking
        progress.stop()


def start(state: AgentState):
    """Initialize the workflow with the input message."""
    return state


def create_workflow(selected_analysts=None, use_debate: bool = False):
    """Create the workflow with selected analysts."""
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)
    workflow.add_node("research_node", research_agent)
    workflow.add_edge("start_node", "research_node")

    # Get analyst nodes from the configuration
    analyst_nodes = get_analyst_nodes()

    # Default to all analysts if none selected
    if selected_analysts is None:
        selected_analysts = list(analyst_nodes.keys())
    # Add selected analyst nodes
    for analyst_key in selected_analysts:
        node_name, node_func = analyst_nodes[analyst_key]
        workflow.add_node(node_name, node_func)
        workflow.add_edge("research_node", node_name)


    # Always add risk and portfolio management
    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_manager", portfolio_management_agent)

    if use_debate:
        workflow.add_node("debate_orchestrator", debate_orchestrator_node)
        for analyst_key in selected_analysts:
            node_name = analyst_nodes[analyst_key][0]
            workflow.add_edge(node_name, "debate_orchestrator")
        workflow.add_edge("debate_orchestrator", "risk_management_agent")
    else:
        for analyst_key in selected_analysts:
            node_name = analyst_nodes[analyst_key][0]
            workflow.add_edge(node_name, "risk_management_agent")

    workflow.add_edge("risk_management_agent", "portfolio_manager")
    workflow.add_edge("portfolio_manager", END)

    workflow.set_entry_point("start_node")
    return workflow


if __name__ == "__main__":
    inputs = parse_cli_inputs(
        description="Run the hedge fund trading system",
        require_tickers=True,
        default_months_back=None,
        include_graph_flag=True,
        include_reasoning_flag=True,
    )

    tickers = [t for t in (inputs.tickers or []) if t and str(t).upper() != "NONE"]
    selected_analysts = inputs.selected_analysts

    # Construct portfolio here
    portfolio = {
        "cash": inputs.initial_cash,
        "margin_requirement": inputs.margin_requirement,
        "margin_used": 0.0,
        "positions": {
            ticker: {
                "long": 0,
                "short": 0,
                "long_cost_basis": 0.0,
                "short_cost_basis": 0.0,
                "short_margin_used": 0.0,
            }
            for ticker in tickers
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,
                "short": 0.0,
            }
            for ticker in tickers
        },
    }

    # Load pre-seeded dossier/transcript if --context-file was passed
    pre_seeded_context = None
    context_file = getattr(inputs, "context_file", None)
    if context_file and os.path.exists(context_file):
        with open(context_file, "r", encoding="utf-8") as _f:
            pre_seeded_context = _f.read()
        print(f"[CONTEXT] Loaded institutional dossier: {context_file} ({len(pre_seeded_context)} chars)")
    elif context_file:
        print(f"[CONTEXT] ⚠️  context-file not found: {context_file}")

    result = run_hedge_fund(
        tickers=tickers,
        start_date=inputs.start_date,
        end_date=inputs.end_date,
        portfolio=portfolio,
        show_reasoning=inputs.show_reasoning,
        selected_analysts=inputs.selected_analysts,
        model_name=inputs.model_name,
        model_provider=inputs.model_provider,
        use_debate=getattr(inputs, "use_debate", False),
        company_name=inputs.company_name,
        pre_seeded_context=pre_seeded_context,
    )
    print_trading_output(result)

    # Trigger live trading and report generation for active trades
    for ticker, decision in result["decisions"].items():
        if decision.get("action", "").lower() != "hold":
            # 1. Execute the trade on Alpaca
            print(f"\n[TRADING] Executing live order for {ticker}...")
            execute_alpaca_trade(ticker, decision)
            
            # 2. Generate the institutional thesis report
            print(f"\n[REPORT] Generating institutional thesis for {ticker}...")
            # Ensure the final state is passed for report generation
            generate_thesis_report(result["state"], ticker, decision)
