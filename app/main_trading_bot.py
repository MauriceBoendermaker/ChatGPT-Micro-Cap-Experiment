import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

from .config_loader import load_settings
from .thesis import load_thesis, save_thesis
from .alpaca_service import make_alpaca, get_account, get_clock, submit_order, get_order
from .market_data import enrich_symbol
from .risk_engine import validate_symbol, make_client_order_id
from .openai_agent import get_portfolio_prompt, ask_openai
from .plotting import plot_weekly_performance
from .storage import save_trade_log, append_total_row, load_latest_total_equity, iso_now_utc
from .portfolio import load_portfolio, summarize_portfolio_for_prompt
from .universe_builder import auto_universe, build_universe
from .risk_controls import breached_daily_drawdown, flatten_all, make_bracket_kwargs
from .db import init_db, insert_trade, update_trade_pnl
from .market_health import market_is_healthy
from .thesis_change import thesis_changed


def update_portfolio_totals(alpaca, portfolio_csv: str) -> None:
    account = get_account(alpaca)
    ts = iso_now_utc()
    row = {
        "Timestamp": ts,
        "Date": ts.split("T")[0],
        "Ticker": "TOTAL",
        "Shares": "",
        "Cost Basis": "",
        "Stop Loss": "",
        "Current Price": "",
        "Total Value": 0.0,
        "PnL": 0.0,
        "Action": "",
        "Cash Balance": float(account.cash),
        "Total Equity": float(account.equity)
    }
    append_total_row(portfolio_csv, row)


def execute_trade(alpaca, order: dict, limit_price: float, settings: dict, dry_run: bool = False, client_order_id: str = "") -> dict:
    side = order["side"]
    symbol = order["ticker"]
    qty = int(order["shares"])
    reason = order.get("reason", "AUTO TRADE")
    if dry_run:
        return {"status": "dry_run", "symbol": symbol, "side": side, "qty": qty, "reason": reason, "limit_price": limit_price}
    kwargs = {"symbol": symbol, "qty": qty, "side": side, "type": "limit", "limit_price": float(limit_price), "time_in_force": "day", "client_order_id": client_order_id}
    kwargs.update(make_bracket_kwargs(float(limit_price), settings))
    o = submit_order(alpaca, **kwargs)
    oid = o.id
    for _ in range(30):
        time.sleep(1)
        s = get_order(alpaca, oid)
        if s.status in {"filled","canceled","rejected","partially_filled","expired"}:
            return {"status": s.status, "symbol": symbol, "side": side, "qty": float(s.filled_qty or 0), "order_id": oid, "reason": reason, "filled_avg_price": float(getattr(s, "filled_avg_price", 0) or 0)}
    s = get_order(alpaca, oid)
    return {"status": s.status, "symbol": symbol, "side": side, "qty": float(s.filled_qty or 0), "order_id": oid, "reason": reason, "filled_avg_price": float(getattr(s, "filled_avg_price", 0) or 0)}


def main():
    init_db()
    load_dotenv()
    settings = load_settings(os.path.join(os.path.dirname(__file__), "config", "settings.json"))
    alpaca = make_alpaca()

    old_equity = load_latest_total_equity(settings["portfolio_csv"])
    start_equity_today = float(get_account(alpaca).equity)

    df, cash_live = load_portfolio(alpaca)
    thesis_path = settings["thesis_file"]
    last_thesis = load_thesis(thesis_path)
    port_json = summarize_portfolio_for_prompt(df)

    uni_syms = auto_universe(alpaca, settings)
    port_prompt = get_portfolio_prompt(port_json, cash_live, last_thesis, week=6) + f" Only choose from: {uni_syms[:50]}"
    ai = ask_openai(port_prompt)

    acct = get_account(alpaca)
    equity_live = float(acct.equity)

    if not thesis_changed(last_thesis, ai.thesis):
        print("Thesis unchanged — skipping trades.")
        update_portfolio_totals(alpaca, settings["portfolio_csv"])
        new_equity = load_latest_total_equity(settings["portfolio_csv"])
        if old_equity == 0:
            print("Baseline set. Daily Change will be meaningful from next run.")
        else:
            print(f"Daily Change: ${new_equity - old_equity:.2f}")
        plot_weekly_performance(settings["portfolio_csv"], settings["plot_dir"], interactive=bool(settings["plot_interactive"]))
        return

    healthy = market_is_healthy(alpaca)

    budget = settings.get("budget", {})
    virtual_equity = float(budget.get("virtual_equity", equity_live))
    max_daily_abs = float(budget.get("max_daily_allocation_abs", float("inf")))
    max_pos_abs = float(budget.get("max_pos_abs", float("inf")))

    buy_candidates = []
    sell_candidates = []

    for o in ai.orders:
        if o.ticker not in uni_syms:
            continue
        meta = enrich_symbol(alpaca, o.ticker)
        if not validate_symbol(meta, settings):
            continue
        price = float(meta["price"])
        if o.side == "sell":
            if not df.empty and o.ticker in df["Ticker"].values:
                owned = int(float(df[df["Ticker"] == o.ticker]["Shares"].iloc[0]))
                if owned > 0:
                    sell_candidates.append({"ticker": o.ticker, "price": price, "max_qty": owned, "reason": o.reason})
            continue
        if healthy:
            buy_candidates.append({"ticker": o.ticker, "price": price, "reason": o.reason})

    buy_candidates = buy_candidates[:settings["risk"]["max_symbols"]]
    remaining = float(settings["budget"]["max_daily_allocation_abs"])
    per_name = remaining / max(1, len(buy_candidates)) if buy_candidates else 0.0

    validated_orders = []
    for c in buy_candidates:
        price = c["price"]
        existing_value = 0.0
        if not df.empty and c["ticker"] in df["Ticker"].values:
            existing_value = float(df[df["Ticker"] == c["ticker"]]["Total Value"].iloc[0])
        pos_room_abs = max(0.0, float(max_pos_abs) - existing_value)
        alloc = min(per_name, pos_room_abs, remaining)
        qty = int(alloc // price)
        if qty <= 0:
            continue
        limit = round(price * 1.01, 2)
        validated_orders.append({"ticker": c["ticker"], "side": "buy", "shares": qty, "reason": c["reason"], "limit_price": limit})
        spent = qty * price
        remaining -= spent

    for c in sell_candidates:
        if c["max_qty"] <= 0:
            continue
        limit = round(c["price"] * 0.99, 2)
        validated_orders.append({"ticker": c["ticker"], "side": "sell", "shares": int(c["max_qty"]), "reason": c["reason"], "limit_price": limit})

    cap = float(settings["budget"]["max_daily_allocation_abs"])
    spent = 0.0
    for i, o in enumerate(validated_orders):
        if o["side"] != "buy":
            continue
        price = float(o.get("limit_price") or 0)
        alloc = o["shares"] * price
        if spent + alloc <= cap:
            spent += alloc
            continue
        room = max(0.0, cap - spent)
        max_qty = int(room // price) if price > 0 else 0
        o["shares"] = max(max_qty, 0)
        spent += o["shares"] * price
    validated_orders = [o for o in validated_orders if o["side"] != "buy" or o["shares"] > 0]

    planned_spend = sum(o["shares"] * (o.get("limit_price") or 0) for o in validated_orders if o["side"] == "buy")
    print(f"Planned spend today: ${planned_spend:.2f} (cap ${settings['budget']['max_daily_allocation_abs']})")
    print("Validated orders:", validated_orders)

    if breached_daily_drawdown(start_equity_today, float(get_account(alpaca).equity), settings) and settings["drawdown"]["flatten_on_breach"]:
        flat = flatten_all(alpaca)
        print("Flattened due to daily drawdown:", flat)
        update_portfolio_totals(alpaca, settings["portfolio_csv"])
        return

    clock = get_clock(alpaca)
    if not clock.is_open:
        print("Market closed; skipping order placement.")
        validated_orders = []

    for vo in validated_orders:
        client_id = make_client_order_id("chatgptbot", vo["ticker"])
        res = execute_trade(alpaca, vo, limit_price=vo["limit_price"], settings=settings, dry_run=bool(settings["dry_run"]), client_order_id=client_id)
        insert_trade(vo["ticker"], vo["side"], int(vo["shares"]), float(vo["limit_price"]), res.get("status",""), int(res.get("qty",0)), float(res.get("filled_avg_price", vo["limit_price"])))
        log = {
            "Timestamp": iso_now_utc(),
            "Date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "Ticker": vo["ticker"],
            "Shares": vo["shares"],
            "Side": vo["side"],
            "Reason": vo.get("reason", ""),
            "OrderStatus": res.get("status", ""),
            "OrderId": res.get("order_id", ""),
            "ClientOrderId": client_id,
            "BudgetVirtualEquity": float(virtual_equity)
        }
        save_trade_log(settings["trade_log_csv"], log)

    save_thesis(thesis_path, ai.thesis or "No thesis returned.")
    update_portfolio_totals(alpaca, settings["portfolio_csv"])

    new_equity = load_latest_total_equity(settings["portfolio_csv"])
    if old_equity == 0:
        print("Baseline set. Daily Change will be meaningful from next run.")
    else:
        print(f"Daily Change: ${new_equity - old_equity:.2f}")

    plot_weekly_performance(settings["portfolio_csv"], settings["plot_dir"], interactive=bool(settings["plot_interactive"]))


if __name__ == "__main__":
    main()
