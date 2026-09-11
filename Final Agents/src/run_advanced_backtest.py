import argparse
from src.backtesting.advanced_engine import AdvancedBacktester
from datetime import datetime
import json

def main():
    parser = argparse.ArgumentParser(description='Run Advanced AI Hedge Fund Backtest')
    parser.add_argument('--tickers', type=str, required=True, help='Comma-separated tickers (e.g. AAPL,MSFT)')
    parser.add_argument('--start', type=str, default='2024-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=datetime.now().strftime('%Y-%m-%d'), help='End date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=100000.0, help='Initial capital')
    
    args = parser.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(',')]
    
    print(f"🚀 Starting Advanced Backtest for {tickers}")
    print(f"📅 Period: {args.start} to {args.end}")
    print(f"💰 Initial Capital: ${args.capital:,.2f}")
    
    # In a real scenario, we would run the agents here to get signals.
    # For this standalone script demo, we simulate agent signals as 'bullish' for the selected tickers
    # to demonstrate the engine's capability.
    simulated_signals = {t: "bullish" for t in tickers}
    
    backtester = AdvancedBacktester(initial_capital=args.capital)
    report = backtester.run(tickers, simulated_signals, args.start, args.end)
    
    print("\n" + "="*50)
    print("📈 BACKTEST REPORT")
    print("="*50)
    print(f"Final Value: ${report['final_value']:,.2f}")
    print(f"Total Return: {report['total_return_pct']:.2f}%")
    print(f"Win Rate: {report['win_rate_pct']:.2f}%")
    print(f"Number of Trades: {report['number_of_trades']}")
    print("-" * 50)
    print("Risk Metrics:")
    print(f"  Sharpe Ratio: {report['metrics']['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {report['metrics']['max_drawdown']:.2f}%")
    print("="*50)
    
    # Output result to file
    with open("backtest_results.json", "w") as f:
        json.dump(report, f, indent=4)
        print("\n✅ Full results saved to backtest_results.json")

if __name__ == "__main__":
    main()
