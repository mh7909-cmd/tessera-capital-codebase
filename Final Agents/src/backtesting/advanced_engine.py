import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import os

class AdvancedBacktester:
    """
    Institutional-grade backtesting engine for agent-driven strategies.
    Handles multiple symbols, portfolio rebalancing, and professional risk metrics.
    """
    def __init__(self, initial_capital: float = 100000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        self.portfolio = {"cash": initial_capital, "positions": {}}
        self.history = []
        self.equity_curve = []

    def fetch_data(self, tickers: List[str], start_date: str, end_date: str):
        """Fetches historical data via yfinance as fallback."""
        data = {}
        for ticker in tickers:
            df = yf.download(ticker, start=start_date, end=end_date)
            if not df.empty:
                data[ticker] = df
        return data

    def run(self, tickers: List[str], agent_signals: Dict[str, Any], start_date: str, end_date: str):
        """
        Runs the backtest loop.
        agent_signals: Dict mapping ticker to signal ('bullish', 'bearish', 'neutral')
        """
        data = self.fetch_data(tickers, start_date, end_date)
        if not data:
            return {"error": "No data found for tickers."}

        # For simplicity in this autonomous version, we use the end_date price for a single rebalance
        # Or we can loop through the full date range if we want a time-series backtest.
        # Given the "Agent Research" focus, we'll do a point-in-time rebalance and then simulate 
        # the performance over the specified window.

        results = {}
        total_value = self.initial_capital
        
        # Determine allocations based on agent signals
        signals = agent_signals  # Ticker -> Signal
        bullish_tickers = [t for t, s in signals.items() if s == "bullish"]
        
        if not bullish_tickers:
            # All cash
            self.equity_curve = [total_value] * 10
            return self.generate_report(total_value, total_value, [])

        # Equal weight allocation among bullish tickers
        allocation_per_ticker = total_value / len(bullish_tickers)
        
        trades = []
        for ticker in bullish_tickers:
            if ticker in data:
                df = data[ticker]
                # Handle potential MultiIndex columns in yfinance 0.2.x
                if isinstance(df.columns, pd.MultiIndex):
                    # Find the 'Close' column for the specific ticker
                    start_price = float(df.xs('Close', axis=1, level=0).iloc[0, 0])
                    end_price = float(df.xs('Close', axis=1, level=0).iloc[-1, 0])
                else:
                    start_price = float(df.iloc[0]["Close"])
                    end_price = float(df.iloc[-1]["Close"])


                shares = (allocation_per_ticker * (1 - self.commission)) / start_price
                final_value = shares * end_price
                pnl = final_value - allocation_per_ticker
                return_pct = (end_price - start_price) / start_price
                
                trades.append({
                    "ticker": ticker,
                    "shares": shares,
                    "entry_price": start_price,
                    "exit_price": end_price,
                    "pnl": pnl,
                    "return_pct": return_pct
                })
                total_value -= allocation_per_ticker
                total_value += final_value

        return self.generate_report(self.initial_capital, total_value, trades)

    def generate_report(self, initial, final, trades):
        total_return = (final - initial) / initial
        win_rate = len([t for t in trades if t["pnl"] > 0]) / len(trades) if trades else 0
        
        report = {
            "initial_capital": initial,
            "final_value": final,
            "total_return_pct": total_return * 100,
            "win_rate_pct": win_rate * 100,
            "number_of_trades": len(trades),
            "trades": trades,
            "metrics": {
                "sharpe_ratio": self.calculate_sharpe(trades),
                "max_drawdown": self.calculate_max_drawdown(trades)
            }
        }
        return report

    def calculate_sharpe(self, trades):
        if not trades: return 0
        returns = [t["return_pct"] for t in trades]
        if len(returns) < 2: return 0
        return np.mean(returns) / np.std(returns) * np.sqrt(252) # Annualized simplified

    def calculate_max_drawdown(self, trades):
        # Simplified for point-in-time
        returns = [t["return_pct"] for t in trades]
        if not returns: return 0
        return min(returns) if min(returns) < 0 else 0
