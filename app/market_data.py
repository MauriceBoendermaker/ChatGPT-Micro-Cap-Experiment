from typing import Optional
from .alpaca_service import get_asset, get_last_trade_price, get_avg_volume


def enrich_symbol(alpaca, symbol: str) -> dict:
    a = get_asset(alpaca, symbol)
    price = get_last_trade_price(alpaca, symbol)
    avg_vol = get_avg_volume(alpaca, symbol, days=20)
    exchange = getattr(a, "exchange", None)
    tradable = bool(getattr(a, "tradable", False))
    marginable = bool(getattr(a, "marginable", False))
    shortable = bool(getattr(a, "shortable", False))
    market_cap = None
    return {
        "symbol": symbol,
        "price": price,
        "avg_volume": avg_vol,
        "exchange": exchange,
        "tradable": tradable,
        "marginable": marginable,
        "shortable": shortable,
        "market_cap": market_cap
    }
