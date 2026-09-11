import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

def execute_alpaca_trade(ticker, decision):
    """
    Executes a market order on Alpaca based on the Portfolio Manager's decision.
    """
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    if not api_key or not secret_key:
        print(f"[TRADING: ERROR] Alpaca credentials missing for {ticker}. Skipping execution.")
        return None

    # Initialize Client
    client = TradingClient(api_key, secret_key, paper=( "paper" in base_url ))

    action = decision.get("action", "").lower()
    quantity = int(decision.get("quantity", 0))

    if action == "hold" or quantity <= 0:
        return None

    # Map signal actions to Alpaca Sides
    side = None
    if action in ["buy", "cover"]:
        side = OrderSide.BUY
    elif action in ["sell", "short"]:
        side = OrderSide.SELL

    if not side:
        print(f"[TRADING: ERROR] Invalid action '{action}' for {ticker}.")
        return None

    # Create Market Order
    order_details = MarketOrderRequest(
        symbol=ticker,
        qty=quantity,
        side=side,
        time_in_force=TimeInForce.DAY
    )

    try:
        order = client.submit_order(order_data=order_details)
        print(f"\n[TRADING] Order submitted for {ticker}: {action.upper()} {quantity} shares.")
        print(f"[TRADING] Order ID: {order.id} | Status: {order.status}")
        return order
    except Exception as e:
        print(f"[TRADING: ERROR] Failed to submit order for {ticker}: {str(e)}")
        return None
