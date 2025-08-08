from typing import Dict, List
from .alpaca_service import list_positions, submit_order


def breached_daily_drawdown(start_equity: float, current_equity: float, settings: dict) -> bool:
    limit = float(settings["drawdown"]["max_daily_loss_pct"])
    if limit <= 0:
        return False
    loss = (start_equity - current_equity) / max(start_equity, 1e-9)
    return loss >= limit


def flatten_all(alpaca) -> List[Dict]:
    res = []
    for p in list_positions(alpaca):
        try:
            side = "sell" if float(p.qty) > 0 else "buy"
            qty = abs(int(float(p.qty)))
            if qty <= 0:
                continue
            o = submit_order(alpaca, symbol=p.symbol, qty=qty, side=side, type="market", time_in_force="day")
            res.append({"symbol": p.symbol, "qty": qty, "side": side, "status": "submitted"})
        except Exception as e:
            res.append({"symbol": p.symbol, "error": str(e)})
    return res


def make_bracket_kwargs(price: float, settings: dict) -> Dict:
    if not settings["brackets"]["use_bracket"]:
        return {}
    sl_pct = float(settings["brackets"]["stop_loss_pct"])
    tp_pct = float(settings["brackets"]["take_profit_pct"])
    trail_pct = float(settings["brackets"]["trailing_stop_pct"])
    if trail_pct > 0:
        return {"order_class": "trailing_stop", "trail_percent": round(trail_pct * 100, 2)}
    stop_price = round(price * (1 - sl_pct), 2)
    limit_price = round(price * (1 + tp_pct), 2)
    return {"order_class": "bracket", "take_profit": {"limit_price": limit_price}, "stop_loss": {"stop_price": stop_price}}
