import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta
import argparse
import questionary
from colorama import Fore, Style

from src.utils.analysts import ANALYST_ORDER
from src.llm.models import LLM_ORDER, OLLAMA_LLM_ORDER, get_model_info, ModelProvider, find_model_by_name
from src.utils.ollama import ensure_ollama_and_model

from dataclasses import dataclass
from typing import Optional


def add_common_args(
    parser: argparse.ArgumentParser,
    *,
    require_tickers: bool = False,
    include_analyst_flags: bool = True,
    include_ollama: bool = True,
) -> argparse.ArgumentParser:
    parser.add_argument(
        "--tickers",
        "--ticker",
        dest="tickers",
        type=str,
        required=require_tickers,
        help="Comma-separated list of stock ticker symbols (e.g., AAPL,MSFT,GOOGL). Alias: --ticker",
    )
    if include_analyst_flags:
        parser.add_argument(
            "--analysts",
            type=str,
            required=False,
            help="Comma-separated list of analysts to use (e.g., michael_burry,other_analyst)",
        )
        parser.add_argument(
            "--analysts-all",
            action="store_true",
            help="Use all available analysts (overrides --analysts)",
        )
    if include_ollama:
        parser.add_argument("--ollama", action="store_true", help="Use Ollama for local LLM inference")
    parser.add_argument("--model", type=str, required=False, help="Model name to use (e.g., gpt-4o)")
    return parser


def add_date_args(parser: argparse.ArgumentParser, *, default_months_back: int | None = None) -> argparse.ArgumentParser:
    if default_months_back is None:
        parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
        parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    else:
        parser.add_argument(
            "--end-date",
            type=str,
            default=datetime.now().strftime("%Y-%m-%d"),
            help="End date in YYYY-MM-DD format",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            default=(datetime.now() - relativedelta(months=default_months_back)).strftime("%Y-%m-%d"),
            help="Start date in YYYY-MM-DD format",
        )
    return parser


def parse_tickers(tickers_arg: str | None) -> list[str]:
    if not tickers_arg:
        return []
    return [ticker.strip() for ticker in tickers_arg.split(",") if ticker.strip()]


def select_analysts(flags: dict | None = None) -> list[str]:
    # Always use all analysts per user request
    choices = [a[1] for a in ANALYST_ORDER]
    
    print(
        f"\nUsing {Fore.GREEN}all analysts{Style.RESET_ALL}: {', '.join(Fore.CYAN + c.title().replace('_', ' ') + Style.RESET_ALL for c in choices)} (Auto-selected)\n"
    )
    return choices


def select_model(use_ollama: bool, model_flag: str | None = None) -> tuple[str, str]:
    # Default to 'hella fast' free NVIDIA NIM model (8B for maximum reliability and speed)
    model_name = "meta/llama-3.1-8b-instruct"
    model_provider = ModelProvider.NVIDIA.value

    # Override if flag is provided
    if model_flag:
        model_info = find_model_by_name(model_flag)
        if model_info:
            model_name = model_info.model_name
            model_provider = model_info.provider.value
        else:
            model_name = model_flag
            # Heuristic for provider
            if "claude" in model_name.lower():
                model_provider = ModelProvider.ANTHROPIC.value
            elif "gpt" in model_name.lower():
                model_provider = ModelProvider.OPENAI.value
            elif "nvidia" in model_name.lower() or "nemotron" in model_name.lower():
                model_provider = ModelProvider.NVIDIA.value

    print(f"\nUsing {Fore.CYAN}{model_provider}{Style.RESET_ALL} model: {Fore.GREEN + Style.BRIGHT}{model_name}{Style.RESET_ALL} (Speed Optimization Enabled)\n")
    
    return model_name, model_provider


def resolve_dates(start_date: str | None, end_date: str | None, *, default_months_back: int | None = None) -> tuple[str, str]:
    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Start date must be in YYYY-MM-DD format")
    if end_date:
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("End date must be in YYYY-MM-DD format")

    final_end = end_date or datetime.now().strftime("%Y-%m-%d")
    if start_date:
        final_start = start_date
    else:
        months = default_months_back if default_months_back is not None else 3
        end_date_obj = datetime.strptime(final_end, "%Y-%m-%d")
        final_start = (end_date_obj - relativedelta(months=months)).strftime("%Y-%m-%d")
    return final_start, final_end


@dataclass
class CLIInputs:
    tickers: list[str]
    selected_analysts: list[str]
    model_name: str
    model_provider: str
    start_date: str
    end_date: str
    initial_cash: float
    margin_requirement: float
    show_reasoning: bool = False
    show_agent_graph: bool = False
    use_debate: bool = False
    company_name: Optional[str] = None
    context_file: Optional[str] = None
    raw_args: Optional[argparse.Namespace] = None


def parse_cli_inputs(
    *,
    description: str,
    require_tickers: bool,
    default_months_back: int | None,
    include_graph_flag: bool = False,
    include_reasoning_flag: bool = False,
) -> CLIInputs:
    parser = argparse.ArgumentParser(description=description)

    # Common/interactive flags
    add_common_args(parser, require_tickers=require_tickers, include_analyst_flags=True, include_ollama=True)
    add_date_args(parser, default_months_back=default_months_back)

    # Funding flags (standardized, with alias)
    parser.add_argument(
        "--initial-cash",
        "--initial-capital",
        dest="initial_cash",
        type=float,
        default=100000.0,
        help="Initial cash position (alias: --initial-capital). Defaults to 100000.0",
    )
    parser.add_argument(
        "--margin-requirement",
        dest="margin_requirement",
        type=float,
        default=0.0,
        help="Initial margin requirement ratio for shorts (e.g., 0.5 for 50%%). Defaults to 0.0",
    )

    if include_reasoning_flag:
        parser.add_argument("--show-reasoning", action="store_true", help="Show reasoning from each agent")
    if include_graph_flag:
        parser.add_argument("--show-agent-graph", action="store_true", help="Show the agent graph")
    parser.add_argument(
        "--debate",
        action="store_true",
        dest="debate",
        default=True,
        help="Run adversarial debate (devil's advocate + meta) after analysts (Enabled by default)",
    )
    # Also add a --no-debate flag for convenience
    parser.add_argument(
        "--no-debate",
        action="store_false",
        dest="debate",
        help="Disable adversarial debate",
    )
    parser.add_argument(
        "--company-name",
        "--company",
        dest="company_name",
        type=str,
        help="Full company name for research search (alias: --company)",
    )
    parser.add_argument(
        "--context-file",
        dest="context_file",
        type=str,
        default=None,
        help="Path to a pre-built institutional dossier/transcript file to inject as research context",
    )

    args = parser.parse_args()

    # Ensure either tickers or company_name is provided
    if not getattr(args, "tickers", None) and not getattr(args, "company_name", None):
        parser.error("At least one of --ticker or --company-name must be provided.")

    # Normalize parsed values
    tickers = parse_tickers(getattr(args, "tickers", None))
    selected_analysts = select_analysts({
        "analysts_all": getattr(args, "analysts_all", False),
        "analysts": getattr(args, "analysts", None),
    })
    model_name, model_provider = select_model(getattr(args, "ollama", False), getattr(args, "model", None))
    start_date, end_date = resolve_dates(getattr(args, "start_date", None), getattr(args, "end_date", None), default_months_back=default_months_back)

    return CLIInputs(
        tickers=tickers,
        selected_analysts=selected_analysts,
        model_name=model_name,
        model_provider=model_provider,
        start_date=start_date,
        end_date=end_date,
        initial_cash=getattr(args, "initial_cash", 100000.0),
        margin_requirement=getattr(args, "margin_requirement", 0.0),
        show_reasoning=getattr(args, "show_reasoning", False),
        show_agent_graph=getattr(args, "show_agent_graph", False),
        use_debate=getattr(args, "debate", False),
        company_name=getattr(args, "company_name", None),
        context_file=getattr(args, "context_file", None),
        raw_args=args,
    )


