import math
import json
import pandas as pd

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
from .config_loader import load_settings
from .alpaca_service import make_alpaca
from .universe_builder import auto_universe
from .market_data import enrich_symbol
from .openai_agent import get_portfolio_prompt, ask_openai


def _bars_close(alpaca, symbol: str, day: datetime) -> float:
    start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    bars = alpaca.get_bars(symbol, "1Day", start.isoformat(), limit=2)
    if not bars:
        return 0.0
    return float(bars[-1].c)


def _bars_open_next(alpaca, symbol: str, day: datetime) -> float:
    nextday = day + timedelta(days=1)
    bars = alpaca.get_bars(symbol, "1Day", day.isoformat(), limit=2)
    if len(bars) < 2:
        return float(bars[0].o) if bars else 0.0
    return float(bars[-1].o)


def run_backtest(start_date: str, end_date: str, settings: dict) -> Dict:
    alpaca = make_alpaca()
    start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    equity = float(settings["budget"]["virtual_equity"])
    cash = equity
    positions = {}
    equity_curve = []
    current_day = start
    while current_day <= end:
        uni = auto_universe(alpaca, settings)
        holdings_json = []
        for sym, pos in positions.items():
            price = _bars_close(alpaca, sym, current_day)
            value = pos * price
            holdings_json.append({"Ticker": sym, "Shares": pos, "Cost Basis": 0.0, "Current Price": price, "Total Value": value})
        port_json = json.dumps(holdings_json)
        prompt = get_portfolio_prompt(port_json, cash, "backtest", week=0) + f" Only choose from: {uni[:20]}"
        ai = ask_openai(prompt)
        buys = []
        for o in ai.orders:
            if o.side != "buy":
                continue
            if o.ticker not in uni:
                continue
            price = _bars_close(alpaca, o.ticker, current_day)
            if price <= 0:
                continue
            buys.append((o.ticker, price))
        if buys:
            alloc = min(float(settings["budget"]["max_daily_allocation_abs"]), cash)
            per = alloc / len(buys)
            for sym, px in buys:
                qty = int(per // px)
                if qty <= 0:
                    continue
                cash -= qty * px
                positions[sym] = positions.get(sym, 0) + qty
        day_value = cash
        for sym, qty in positions.items():
            day_value += qty * _bars_close(alpaca, sym, current_day)
        equity = day_value
        equity_curve.append({"date": current_day.isoformat(), "equity": equity})
        current_day += timedelta(days=1)
    df = pd.DataFrame(equity_curve)
    ret = df["equity"].pct_change().fillna(0)
    sharpe = (ret.mean() / (ret.std() + 1e-9)) * (252 ** 0.5)
    max_dd = 0.0
    peak = -1e18
    for v in df["equity"]:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return {"final_equity": float(df["equity"].iloc[-1]), "sharpe": float(sharpe), "max_drawdown": float(max_dd), "equity_curve": equity_curve}
