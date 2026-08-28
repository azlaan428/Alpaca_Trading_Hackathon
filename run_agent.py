import time
from hedge_signal import run_hedge_check

WATCHLIST = ["AAPL", "MSFT", "TSLA"]
CHECK_INTERVAL_SECONDS = 300  # 5 minutes


def run_watchlist_once():
    for symbol in WATCHLIST:
        run_hedge_check(symbol)


def run_forever():
    while True:
        run_watchlist_once()
        print(f"Sleeping {CHECK_INTERVAL_SECONDS}s until next check...")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()