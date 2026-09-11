"""Smoke integration run for a single ticker with mocked APIs and LLM.

This script stubs network/LLM calls so we can execute the full agent workflow
locally and inspect the debate/devil/meta interactions and final portfolio
manager decisions.

Run from the repo root:
    python3 scripts/smoke_integration.py
"""

from types import SimpleNamespace, ModuleType
import sys
import json

# Create lightweight stubs for external libs that may not be installed
# so we can import the project's modules without pulling heavy deps.
langchain_core = ModuleType("langchain_core")
langchain_core.messages = ModuleType("langchain_core.messages")
langchain_core.prompts = ModuleType("langchain_core.prompts")

class HumanMessage:
    def __init__(self, content: str, name: str | None = None):
        self.content = content
        self.name = name

class BaseMessage:
    def __init__(self, content: str = "", name: str | None = None):
        self.content = content
        self.name = name

    def __repr__(self):
        return f"BaseMessage(name={self.name}, content={self.content!r})"

class ChatPromptTemplate:
    def __init__(self, messages=None):
        self.messages = messages or []

    @classmethod
    def from_messages(cls, messages):
        return cls(messages)

    def invoke(self, data: dict | None = None):
        # produce a simple string representation of the prompt
        return "[PROMPT] " + json.dumps({"messages": self.messages, "data": data}, default=str)

langchain_core.messages.HumanMessage = HumanMessage
langchain_core.messages.BaseMessage = BaseMessage
langchain_core.prompts.ChatPromptTemplate = ChatPromptTemplate

# Minimal langgraph.graph.StateGraph stub only if imported; we will not rely on
# its runtime execution in this smoke script, but defining it prevents import
# failures for code that references it at module import time.
langgraph = ModuleType("langgraph")
langgraph.graph = ModuleType("langgraph.graph")

class StateGraph:
    def __init__(self, *args, **kwargs):
        self._nodes = {}
        self._edges = []

    def add_node(self, name, func):
        self._nodes[name] = func

    def add_edge(self, a, b):
        self._edges.append((a, b))

    def set_entry_point(self, name):
        self._entry = name

    def compile(self):
        # Return a callable object with invoke that runs nodes in insertion order.
        nodes = list(self._nodes.items())

        class Runner:
            def invoke(self, payload):
                state = payload
                # naive run: call each node function with state
                for name, fn in nodes:
                    try:
                        out = fn(state)
                        # merge results if dict-like
                        if isinstance(out, dict):
                            state["messages"] = out.get("messages", state.get("messages", []))
                            state["data"] = out.get("data", state.get("data", {}))
                    except Exception:
                        pass
                return state

        return Runner()

langgraph.graph.StateGraph = StateGraph
langgraph.graph.END = "END"

# Inject stubs into sys.modules so `import` picks them up
sys.modules["langchain_core"] = langchain_core
sys.modules["langchain_core.messages"] = langchain_core.messages
sys.modules["langchain_core.prompts"] = langchain_core.prompts
sys.modules["langgraph"] = langgraph
sys.modules["langgraph.graph"] = langgraph.graph
# lightweight stub for questionary (CLI prompts) so imports succeed
import types as _types
sys.modules["questionary"] = _types.ModuleType("questionary")

# Now import the public API of the system
from src.main import run_hedge_fund

# Models we will construct as fake LLM outputs
from src.agents.cot_schema import default_cot
from src.agents.devil_advocate_agent import DevilAdvocateOutput
from src.agents.meta_agent import MetaAgentOutput
from src.agents.portfolio_manager import PortfolioManagerOutput, PortfolioDecision

# Patch the API and LLM calls by monkey-patching module functions
import src.tools.api as api_mod
import src.utils.llm as llm_mod

# --- Fake data / API stubs -------------------------------------------------

class FakePrice:
    def __init__(self, t, o, c, h, l, v):
        self.time = t
        self.open = o
        self.close = c
        self.high = h
        self.low = l
        self.volume = v
    def model_dump(self):
        return {
            "time": self.time,
            "open": self.open,
            "close": self.close,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
        }


def fake_get_prices(ticker, start_date, end_date, api_key=None):
    # Two point series so returns and volatility compute correctly
    return [
        FakePrice(f"{start_date}T00:00:00Z", 100.0, 110.0, 111.0, 99.0, 1000),
        FakePrice(f"{end_date}T00:00:00Z", 110.0, 120.0, 121.0, 109.0, 1000),
    ]


def fake_prices_to_df(prices):
    # Reuse existing helper which expects objects with model_dump
    return api_mod.prices_to_df(prices)


def fake_get_financial_metrics(ticker, end_date, period="ttm", limit=10, api_key=None):
    # Return a list of simple objects with commonly accessed attributes
    # Most agents will be tolerant of limited fields for this smoke run.
    return [
        SimpleNamespace(
            revenue=1000.0,
            return_on_invested_capital=0.12,
            beta=1.1,
            debt_to_equity=0.4,
            ebit=200.0,
            interest_expense=10.0,
            free_cash_flow=150.0,
            price_to_earnings_ratio=15.0,
            return_on_equity=0.18,
            operating_margin=0.2,
            current_ratio=2.0,
        )
    ]


def fake_search_line_items(ticker, line_items, end_date, period="ttm", limit=10, api_key=None):
    # Provide minimal line items used by agents
    return [
        SimpleNamespace(
            free_cash_flow=150.0,
            ebit=200.0,
            interest_expense=10.0,
            capital_expenditure=-30.0,
            depreciation_and_amortization=20.0,
            outstanding_shares=100.0,
            net_income=120.0,
            total_debt=50.0,
            shareholders_equity=500.0,
            current_assets=300.0,
            current_liabilities=100.0,
            gross_margin=0.45,
            revenue=1000.0,
        )
    ]


def fake_get_company_news(ticker, end_date, start_date=None, limit=1000, api_key=None):
    return []


def fake_get_insider_trades(ticker, end_date, start_date=None, limit=1000, api_key=None):
    return []

# Apply the API stubs
api_mod.get_prices = fake_get_prices
api_mod.prices_to_df = fake_prices_to_df
api_mod.get_financial_metrics = fake_get_financial_metrics
api_mod.search_line_items = fake_search_line_items
api_mod.get_company_news = fake_get_company_news
api_mod.get_insider_trades = fake_get_insider_trades

# --- Fake LLM ----------------------------------------------------------------

def fake_call_llm(prompt, pydantic_model, agent_name=None, state=None, max_retries=3, default_factory=None):
    """Return deterministic, sensible objects depending on requested model class."""
    # If the expected model is the chain-of-thought CotAgentStructuredOutput
    try:
        model_name = pydantic_model.__name__
    except Exception:
        model_name = str(pydantic_model)

    # For many persona agents, they ask for CotAgentStructuredOutput
    if pydantic_model.__name__ == "CotAgentStructuredOutput":
        # Return a default but with agent set appropriately
        cot = default_cot(agent_name or "agent")
        return cot

    if pydantic_model.__name__ == "DevilAdvocateOutput":
        return DevilAdvocateOutput(
            reasoning_steps=[
                "I find no position; I stress test the group",
                "Key assumption overweights growth",
                "Liquidity risk is underappreciated",
                "Valuation sensitive to margins",
                "I would change if forensic accounting proves otherwise",
            ],
            overlooked_risks=["Liquidity shock"],
            false_assumptions=["Stable margins"],
        )

    if pydantic_model.__name__ == "MetaAgentOutput":
        return MetaAgentOutput(
            conviction_score=25.0,
            position_size_pct=1.5,
            investment_thesis="The business is reasonably priced. Diversify. Monitor margins.",
            signal="bullish",
        )

    if pydantic_model.__name__ == "PortfolioManagerOutput":
        # Provide a simple decision: buy 1 share with moderate confidence
        dec = {
            "TEST": PortfolioDecision(action="buy", quantity=1, confidence=70, reasoning="Small starter")
        }
        return PortfolioManagerOutput(decisions=dec)

    # fallback: try to construct a pydantic model with defaults or call default_factory
    if default_factory:
        return default_factory()

    try:
        return pydantic_model()
    except Exception:
        # As a last resort return an empty dict-like object if allowed
        return {}

# Patch the call_llm
llm_mod.call_llm = fake_call_llm

# --- Run the hedge fund workflow ----------------------------------------------

if __name__ == "__main__":
    tickers = ["TEST"]
    start_date = "2024-01-01"
    end_date = "2024-06-01"

    # Build portfolio similar to CLI
    portfolio = {
        "cash": 100000.0,
        "margin_requirement": 0.5,
        "margin_used": 0.0,
        "positions": {"TEST": {"long": 0, "short": 0, "long_cost_basis": 0.0, "short_cost_basis": 0.0, "short_margin_used": 0.0}},
        "realized_gains": {"TEST": {"long": 0.0, "short": 0.0}},
    }

    print("Running smoke integration with mocked APIs/LLM (debate enabled) for ticker TEST...\n")

    result = run_hedge_fund(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        portfolio=portfolio,
        show_reasoning=True,
        selected_analysts=None,  # None -> all analysts
        model_name="gpt-4.1",
        model_provider="OpenAI",
        use_debate=True,
    )

    print("\n===== RESULT =====")
    print(json.dumps(result, indent=2, default=str))

    # Save to file for easier inspection
    with open("smoke_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print("\nSaved smoke_result.json")
