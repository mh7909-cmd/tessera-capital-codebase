import importlib.util
import sys
from colorama import Fore, Style
from tabulate import tabulate
import os
import json
import time

# Try to import ANALYST_ORDER, handle error if not found
try:
    from .analysts import ANALYST_ORDER
except ImportError:
    ANALYST_ORDER = [
        ("Fundamentals Analyst", "bullish"),
        ("Growth Analyst", "bullish"),
        ("Value Analyst", "bearish"),
        ("Sentiment Analyst", "neutral"),
    ]

def stream_institutional_text(text: str, prefix: str = "   ", width: int = 70, delay: float = 0.05):
    """Prints text line-by-line with professional wrapping and a cinematic heartbeat."""
    import textwrap
    paragraphs = text.split('\n')
    for p in paragraphs:
        if not p.strip():
            print("")
            continue
        wrapped = textwrap.fill(p.strip(), width=width, initial_indent=prefix, subsequent_indent=prefix)
        for line in wrapped.split('\n'):
            print(line)
            sys.stdout.flush()
            time.sleep(delay)

def sort_agent_signals(signals):
    """Sort agent signals in a consistent order."""
    analyst_order = {display: idx for idx, (display, _) in enumerate(ANALYST_ORDER)}
    # Add common aliases or additional agents
    analyst_order["Risk Management"] = len(ANALYST_ORDER)
    analyst_order["Meta Agent"] = len(ANALYST_ORDER) + 1
    
    return sorted(signals, key=lambda x: analyst_order.get(x[0], 999))

def print_trading_output(result: dict) -> None:
    """
    Print formatted trading results with high-fidelity cinematic output.
    """
    decisions = result.get("decisions")
    if not decisions:
        print(f"{Fore.RED}No trading decisions available{Style.RESET_ALL}")
        return

    # 1. Global Strategy Extraction
    portfolio_manager_reasoning = ""
    meta_agent_output = result.get("meta_agent_output") or {}
    if isinstance(meta_agent_output, dict):
        for t_idx, t_data in meta_agent_output.items():
            if isinstance(t_data, dict) and t_data.get("investment_thesis"):
                portfolio_manager_reasoning = t_data.get("investment_thesis")
                break

    # 2. Per-Ticker Detailed Analysis
    for ticker, decision in decisions.items():
        print(f"\n{Fore.WHITE}{Style.BRIGHT}INSTITUTIONAL ANALYSIS: {Fore.CYAN}{ticker}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Style.BRIGHT}{'=' * 60}{Style.RESET_ALL}")
        time.sleep(1.0)

        # Prepare analyst signals table
        table_data = []
        for agent, signals in result.get("analyst_signals", {}).items():
            if ticker not in signals:
                continue
                
            if agent == "risk_management_agent":
                continue

            signal = signals[ticker]
            agent_name = agent.replace("_agent", "").replace("_", " ").title()
            signal_type = signal.get("signal", "").upper()
            confidence = signal.get("confidence", 0)

            signal_color = {
                "BULLISH": Fore.GREEN,
                "BEARISH": Fore.RED,
                "NEUTRAL": Fore.YELLOW,
            }.get(signal_type, Fore.WHITE)
            
            reasoning = signal.get("reasoning", "")
            conviction = signal.get("conviction_reason", "")
            steps = signal.get("reasoning_steps", [])
            
            # Build a rich multi-sentence rationale
            parts = []
            
            # Add conviction reason as the lead sentence
            if conviction and conviction not in ("Insufficient data", "Error in analysis, using default", ""):
                parts.append(conviction)
            
            # Add reasoning steps as supporting evidence (skip generic filler)
            FILLER = {"Institutional risk factor identified.", "Insufficient data for a full thesis.",
                      "Criteria could not be evaluated.", "Default score 0.", "No conviction.", "N/A",
                      "Default step"}
            for step in (steps or []):
                step_str = str(step).strip()
                if step_str and step_str not in FILLER and step_str not in parts:
                    parts.append(step_str)
            
            # Fall back to raw reasoning if still empty
            if not parts and reasoning:
                parts.append(str(reasoning))
                
            reasoning_str = " ".join(parts).replace("\u2014", "—").replace("\\u2014", "—").strip()
            if not reasoning_str:
                reasoning_str = "Analysis synthesized from institutional data."
            
            table_data.append([
                agent_name,
                signal_type,
                confidence,
                reasoning_str,
                signal_color
            ])

        # Sort signals
        table_data = sort_agent_signals(table_data)

        # Cinematic Sequential Reveal
        for i, (agent_display, signal_type, confidence, reasoning, color) in enumerate(table_data):
            print(f"\n[{Fore.CYAN}AGENT {i+1}/{len(table_data)}{Style.RESET_ALL}] {Fore.WHITE}{Style.BRIGHT}{agent_display}{Style.RESET_ALL}")
            time.sleep(0.2)
            print(f"   Lean: {color}{signal_type}{Style.RESET_ALL} | Conviction: {Fore.WHITE}{confidence}%{Style.RESET_ALL}")
            time.sleep(0.2)
            
            # Wrap and print rationale using the new institutional streamer
            print(f"{Fore.WHITE}   Rationale:{Style.RESET_ALL}")
            stream_institutional_text(reasoning, prefix="   ", width=65, delay=0.03)
            print(f"{Fore.BLACK}{Style.BRIGHT}{'-' * 60}{Style.RESET_ALL}")
            time.sleep(0.5) # Heartbeat pause (reduced for theatrical pacing)

        # Trading Verdict for this ticker
        print(f"\n{Fore.WHITE}{Style.BRIGHT}FINAL INVESTMENT VERDICT: {Fore.CYAN}{ticker}{Style.RESET_ALL}")
        time.sleep(2.0)
        
        action = decision.get("action", "").upper()
        action_color = {
            "BUY": Fore.GREEN, "SELL": Fore.RED, "HOLD": Fore.YELLOW,
            "COVER": Fore.GREEN, "SHORT": Fore.RED,
        }.get(action, Fore.WHITE)

        reasoning = str(decision.get("reasoning", "")).replace("\u2014", "—")
        
        trading_table = [
            [f"{Fore.WHITE}Action", f"{action_color}{action}{Style.RESET_ALL}"],
            [f"{Fore.WHITE}Quantity", f"{Fore.WHITE}{decision.get('quantity')}{Style.RESET_ALL}"],
            [f"{Fore.WHITE}Confidence", f"{Fore.WHITE}{decision.get('confidence'):.1f}%{Style.RESET_ALL}"],
        ]
        
        print(tabulate(trading_table, tablefmt="simple"))
        print(f"\n{Fore.WHITE}Thesis: {Style.RESET_ALL}")
        stream_institutional_text(reasoning, prefix="   ", width=65, delay=0.03)
        print(f"{Fore.BLACK}{Style.BRIGHT}{'=' * 60}{Style.RESET_ALL}")
        time.sleep(2.0)

    # 3. Portfolio Summary (Global)
    print(f"\n{Fore.WHITE}{Style.BRIGHT}PORTFOLIO RISK ARCHITECTURE:{Style.RESET_ALL}")
    time.sleep(1.0)
    
    portfolio_rows = []
    for tkr, dec in decisions.items():
        sigs = result.get("analyst_signals", {})
        counts = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
        for _, a_sigs in sigs.items():
            if tkr in a_sigs:
                s = a_sigs[tkr].get("signal", "").upper()
                if s in counts: counts[s] += 1
        
        portfolio_rows.append([
            f"{Fore.CYAN}{tkr}{Style.RESET_ALL}",
            f"{Fore.WHITE}{dec.get('action', '').upper()}{Style.RESET_ALL}",
            f"{Fore.WHITE}{dec.get('quantity')}{Style.RESET_ALL}",
            f"{Fore.WHITE}{dec.get('confidence'):.1f}%{Style.RESET_ALL}",
            f"{Fore.GREEN}{counts['BULLISH']}{Style.RESET_ALL}",
            f"{Fore.RED}{counts['BEARISH']}{Style.RESET_ALL}",
            f"{Fore.YELLOW}{counts['NEUTRAL']}{Style.RESET_ALL}",
        ])

    headers = [f"{Fore.WHITE}Ticker", "Action", "Qty", "Conf", "Bull", "Bear", "Neut"]
    print(tabulate(portfolio_rows, headers=headers, tablefmt="grid"))
    time.sleep(2.0)
    
    if portfolio_manager_reasoning:
        print(f"\n{Fore.WHITE}{Style.BRIGHT}CHIEF INVESTMENT OFFICER STRATEGY:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Style.BRIGHT}{'-' * 35}{Style.RESET_ALL}")
        clean_pm = str(portfolio_manager_reasoning).replace("\u2014", "—").replace("\\n", "\n")
        stream_institutional_text(clean_pm, prefix="   ", width=70, delay=0.05)
        print(f"{Fore.WHITE}{Style.BRIGHT}{'-' * 35}{Style.RESET_ALL}\n")
        time.sleep(2.0)

def print_backtest_results(table_rows: list) -> None:
    """Print the backtest results in a nicely formatted table"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\n{Fore.WHITE}{Style.BRIGHT}HISTORICAL BACKTEST PERFORMANCE:{Style.RESET_ALL}")
    headers = ["Metric", "Value"]
    print(tabulate(table_rows, headers=headers, tablefmt="grid"))
    print("\n")
