import math

from typing import List, Dict
from .alpaca_service import get_asset, get_last_trade_price, get_avg_volume


def build_universe(alpaca, symbols: List[str]) -> List[Dict]:
    universe = []
    for sym in symbols:
        try:
            a = get_asset(alpaca, sym)
            price = get_last_trade_price(alpaca, sym)
            vol = get_avg_volume(alpaca, sym, days=20)
            exchange = getattr(a, "exchange", None)
            tradable = bool(getattr(a, "tradable", False))
            universe.append({"symbol": sym, "price": float(price), "avg_volume": float(vol), "exchange": exchange, "tradable": tradable})
        except Exception:
            continue
    return universe


def auto_universe(alpaca, settings: dict) -> List[str]:
    exchanges = set(settings["universe"]["exchanges"])
    min_price = float(settings["universe"]["min_price"])
    max_price = float(settings["universe"]["max_price"])
    min_avg_volume = float(settings["universe"]["min_avg_volume"])
    max_size = int(settings["universe"]["max_size"])
    assets = alpaca.list_assets(status="active", asset_class="us_equity")
    candidates = []

    for a in assets:
        if a.exchange not in exchanges:
            continue
        if not a.tradable:
            continue
        try:
            price = get_last_trade_price(alpaca, a.symbol)
            if price < min_price or price > max_price:
                continue
            avgv = get_avg_volume(alpaca, a.symbol, days=20)
            if avgv < min_avg_volume:
                continue
            candidates.append((a.symbol, avgv))
        except Exception:
            continue

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in candidates[:max_size]]
