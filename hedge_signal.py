from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

from execution import place_order, get_option_contract

load_dotenv()

data_client = StockHistoricalDataClient(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"))

DROP_THRESHOLD_PCT = 0.03  # trigger a hedge if price dropped more than 3% from its recent high


def get_recent_prices(symbol, days=10):
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=days),
    )
    bars = data_client.get_stock_bars(request)
    return [bar.close for bar in bars[symbol]]


def check_for_drop(symbol):
    """Return True if the stock dropped more than DROP_THRESHOLD_PCT from its recent high."""
    prices = get_recent_prices(symbol)
    if len(prices) < 2:
        print(f"Not enough price data for {symbol}")
        return False

    recent_high = max(prices)
    current_price = prices[-1]
    drop_pct = (recent_high - current_price) / recent_high

    print(f"{symbol}: high={recent_high:.2f}, current={current_price:.2f}, drop={drop_pct:.2%}")
    return drop_pct >= DROP_THRESHOLD_PCT


def run_hedge_check(symbol):
    """If the stock has dropped enough, buy a protective put."""
    if check_for_drop(symbol):
        contract = get_option_contract(symbol)
        print(f"Drop detected on {symbol} -- buying protective put {contract.symbol}")
        place_order(contract.symbol, "buy", qty=1, price_per_contract=float(contract.close_price or 0))
    else:
        print(f"No significant drop on {symbol}, no action taken")


if __name__ == "__main__":
    run_hedge_check("AAPL")