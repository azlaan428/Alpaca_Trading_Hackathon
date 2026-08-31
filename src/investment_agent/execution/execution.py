from alpaca.trading.enums import OrderSide, TimeInForce, ContractType
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOptionContractsRequest
from dotenv import load_dotenv
import os

load_dotenv()

client = TradingClient(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=True)


def get_option_contract(underlying_symbol, expiration=None, strike=None, option_type=None):
    """Fetch a single option contract matching the given criteria."""
    contract_type = None
    if option_type:
        contract_type = ContractType.PUT if option_type.lower() == "put" else ContractType.CALL

    request = GetOptionContractsRequest(
        underlying_symbols=[underlying_symbol],
        type=contract_type,
        limit=1,
    )
    contracts = client.get_option_contracts(request).option_contracts
    if not contracts:
        raise ValueError(f"No option contracts found for {underlying_symbol}")
    return contracts[0]

MAX_POSITION_PCT = 0.05  # never risk more than 5% of buying power on one trade


def is_trade_safe(symbol, qty, price_per_contract):
    if not price_per_contract or price_per_contract <= 0:
        print(f"BLOCKED: no valid price for {symbol}, can't verify trade size safely")
        return False

    account = client.get_account()
    buying_power = float(account.buying_power)
    trade_cost = qty * price_per_contract * 100  # options are priced per share, 100 shares per contract
    max_allowed = buying_power * MAX_POSITION_PCT
    if trade_cost > max_allowed:
        print(f"BLOCKED: trade costs ${trade_cost:.2f}, limit is ${max_allowed:.2f}")
        return False
    return True

def place_order(symbol, side, qty, price_per_contract):
    """Place a market order (stock or option symbol) and return the order result, after a safety check."""
    if not is_trade_safe(symbol, qty, price_per_contract):
        return None
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=order_side,
        time_in_force=TimeInForce.DAY,
    )
    result = client.submit_order(order)
    print(f"{side.upper()} {qty}x {symbol} -> status: {result.status}, id: {result.id}")
    return result

def get_account_summary():
    """Return current account status and buying power."""
    account = client.get_account()
    return {"status": account.status, "buying_power": account.buying_power}


if __name__ == "__main__":
    print(get_account_summary())
    contract = get_option_contract("AAPL")
    place_order(contract.symbol, "buy", qty=1, price_per_contract=float(contract.close_price or 0))