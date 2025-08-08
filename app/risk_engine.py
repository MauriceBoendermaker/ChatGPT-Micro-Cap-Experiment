import math
import uuid


def clamp_qty_by_cash(shares: float, price: float, cash: float) -> int:
    if price <= 0:
        return 0
    max_affordable = int(math.floor(cash // price))
    return min(int(math.floor(shares)), max_affordable)


def validate_symbol(meta: dict, settings: dict) -> bool:
    ex_ok = meta.get("exchange") in settings["universe"]["exchanges"]
    price_ok = meta.get("price", 0) >= settings["risk"]["min_price"]
    vol_ok = meta.get("avg_volume", 0) >= settings["risk"]["min_avg_volume"]
    mc = meta.get("market_cap")
    mc_ok = True if mc is None else mc <= settings["risk"]["max_market_cap"]
    tradable_ok = bool(meta.get("tradable"))
    return ex_ok and price_ok and vol_ok and mc_ok and tradable_ok


def enforce_position_limits(symbol: str, qty: int, price: float, account_equity: float, current_positions_value: dict, settings: dict) -> int:
    max_pos_value = settings["risk"]["max_pos_pct"] * account_equity
    desired_value = qty * price
    if desired_value <= max_pos_value:
        return qty
    limited_qty = int(max_pos_value // price)
    return max(limited_qty, 0)


def within_max_symbols(symbols_after: set, settings: dict) -> bool:
    return len(symbols_after) <= settings["risk"]["max_symbols"]


def max_daily_allocation_ok(new_allocation_value: float, account_equity: float, settings: dict) -> bool:
    return new_allocation_value <= settings["risk"]["max_daily_allocation_pct"] * account_equity


def make_client_order_id(prefix: str, symbol: str) -> str:
    return f"{prefix}_{symbol}_{uuid.uuid4().hex[:8]}"
