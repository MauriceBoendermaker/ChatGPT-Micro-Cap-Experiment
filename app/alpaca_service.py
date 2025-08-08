import os

from alpaca_trade_api.rest import REST, TimeFrame


def make_alpaca():
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    base = os.getenv("ALPACA_BASE_URL")
    return REST(key, secret, base)


def get_account(alpaca: REST):
    return alpaca.get_account()


def get_clock(alpaca: REST):
    return alpaca.get_clock()


def list_positions(alpaca: REST):
    return alpaca.list_positions()


def get_asset(alpaca: REST, symbol: str):
    return alpaca.get_asset(symbol)


def get_latest_trade(alpaca: REST, symbol: str):
    return alpaca.get_latest_trade(symbol)


def get_latest_quote(alpaca: REST, symbol: str):
    return alpaca.get_latest_quote(symbol)


def get_last_trade_price(alpaca: REST, symbol: str) -> float:
    t = alpaca.get_latest_trade(symbol)
    return float(t.price)


def get_bars(alpaca: REST, symbol: str, tf: TimeFrame, limit: int = 20):
    return alpaca.get_bars(symbol, tf, limit=limit)


def get_avg_volume(alpaca: REST, symbol: str, days: int = 20) -> float:
    bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=days)
    if not bars:
        return 0.0
    vols = [float(b.v) for b in bars]
    return sum(vols) / len(vols)


def submit_order(alpaca: REST, **kwargs):
    return alpaca.submit_order(**kwargs)


def get_order(alpaca: REST, order_id: str):
    return alpaca.get_order(order_id)
