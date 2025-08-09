import time

from typing import List
from alpaca_trade_api.rest import TimeFrame
from .alpaca_service import get_bars_multi


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]


def auto_universe(alpaca, settings: dict) -> List[str]:
    exchanges = set(settings["universe"]["exchanges"])
    min_price = float(settings["universe"]["min_price"])
    max_price = float(settings["universe"]["max_price"])
    min_avg_volume = float(settings["universe"]["min_avg_volume"])
    max_size = int(settings["universe"]["max_size"])
    scan_cap = int(settings["universe"].get("max_scan", 1200))
    days = int(settings["universe"].get("avg_volume_days", 20))
    chunk_size = int(settings["universe"].get("batch_size", 200))
    timeout_seconds = int(settings["universe"].get("timeout_seconds", 20))

    assets = alpaca.list_assets(status="active", asset_class="us_equity")
    syms = [a.symbol for a in assets if a.exchange in exchanges and a.tradable][:scan_cap]
    start_t = time.monotonic()

    scored = []
    for batch in _chunks(syms, chunk_size):
        if time.monotonic() - start_t > timeout_seconds:
            break
        bars = get_bars_multi(alpaca, batch, TimeFrame.Day, limit=days)
        by_sym = {}
        for b in bars:
            by_sym.setdefault(b.S, []).append(b)

        for s in batch:
            sb = by_sym.get(s, [])
            if not sb:
                continue
            closes = [float(x.c) for x in sb if float(x.c) > 0]
            vols = [float(x.v) for x in sb if float(x.v) > 0]
            if not closes or not vols:
                continue
            last_px = closes[-1]
            avgv = sum(vols)/len(vols)
            if last_px < min_price or last_px > max_price:
                continue
            if avgv < min_avg_volume:
                continue
            scored.append((s, avgv))

        if len(scored) >= max_size*2:
            break

    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s,_ in scored[:max_size]]