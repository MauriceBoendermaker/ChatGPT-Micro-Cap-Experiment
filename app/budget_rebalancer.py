import json
import math

from typing import Tuple


def _round_to(x: float, step: float) -> float:
    if step <= 0:
        return x
    return step * round(x/step)


def rebalance(virtual_equity: float, base_equity: float, current_equity: float, settings: dict) -> Tuple[float, bool]:
    if not settings.get("rebalance", {}).get("enabled", False):
        return virtual_equity, False
    up_pct = float(settings["rebalance"]["up_pct"])
    down_pct = float(settings["rebalance"]["down_pct"])
    min_v = float(settings["rebalance"]["min_virtual"])
    max_v = float(settings["rebalance"]["max_virtual"])
    step = float(settings["rebalance"]["round_to"])
    if base_equity <= 0:
        return virtual_equity, False
    change = (current_equity - base_equity) / base_equity
    target = virtual_equity
    changed = False
    if change >= up_pct:
        target = min(max_v, virtual_equity * (1.0 + up_pct))
        changed = True
    elif change <= -down_pct:
        target = max(min_v, virtual_equity * (1.0 - down_pct))
        changed = True
    if changed:
        target = _round_to(target, step)
    return float(target), changed


def save_virtual_equity(settings_path: str, settings: dict, new_virtual: float):
    settings["budget"]["virtual_equity"] = float(new_virtual)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
