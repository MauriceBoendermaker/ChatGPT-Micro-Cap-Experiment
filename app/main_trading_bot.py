import os
import json
import time
import pandas as pd

from datetime import datetime, timezone
from dotenv import load_dotenv

from .config_loader import load_settings
from .thesis import load_thesis, save_thesis
from .alpaca_service import make_alpaca, get_account, get_clock, list_positions, submit_order, get_order
from .market_data import enrich_symbol
from .risk_engine import clamp_qty_by_cash, validate_symbol, enforce_position_limits, within_max_symbols, max_daily_allocation_ok, make_client_order_id
from .openai_agent import get_portfolio_prompt, ask_openai
from .plotting import plot_weekly_performance
from .storage import save_trade_log, append_total_row, load_latest_total_equity, iso_now_utc
from .portfolio import load_portfolio, summarize_portfolio_for_prompt


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


def execute_trade(alpaca, order: dict, dry_run: bool = False, client_order_id: str = "") -> dict:
    side = order["side"]
    symbol = order["ticker"]
    qty = order["shares"]
    reason = order.get("reason", "AUTO TRADE")

    if dry_run:
        return {"status": "dry_run", "symbol": symbol, "side": side, "qty": qty, "reason": reason}

    o = submit_order(
        alpaca,
        symbol=symbol,
        qty=qty,
        side=side,
        type="limit" if side in {"buy","sell"} else "market",
        time_in_force="day",
        client_order_id=client_order_id
    )

    oid = o.id

    for _ in range(30):
        time.sleep(1)
        s = get_order(alpaca, oid)

        if s.status in {"filled","canceled","rejected","partially_filled","expired"}:
            return {"status": s.status, "symbol": symbol, "side": side, "qty": float(s.filled_qty or 0), "order_id": oid, "reason": reason}

    s = get_order(alpaca, oid)
    return {"status": s.status, "symbol": symbol, "side": side, "qty": float(s.filled_qty or 0), "order_id": oid, "reason": reason}


def main():
    load_dotenv()

    settings = load_settings(os.path.join(os.path.dirname(__file__), "config", "settings.json"))
    alpaca = make_alpaca()
    old_equity = load_latest_total_equity(settings["portfolio_csv"])
    df, cash = load_portfolio(alpaca)
    thesis_path = settings["thesis_file"]
    last_thesis = load_thesis(thesis_path)
    port_json = summarize_portfolio_for_prompt(df)
    prompt = get_portfolio_prompt(port_json, cash, last_thesis, week=6)
    ai = ask_openai(prompt)
    acct = get_account(alpaca)
    equity = float(acct.equity)
    symbols_before = set(df["Ticker"].tolist()) if not df.empty else set()
    total_new_alloc = 0.0
    validated_orders = []

    for o in ai.orders:
        meta = enrich_symbol(alpaca, o.ticker)
        ok = validate_symbol(meta, settings)

        if not ok:
            continue

        positions_value = {}

        if not df.empty:
            for _, r in df.iterrows():
                positions_value[r["Ticker"]] = float(r["Total Value"])

        price = float(meta["price"])
        available_cash = float(get_account(alpaca).cash)
        qty_cash_clamped = clamp_qty_by_cash(o.shares, price, available_cash)

        if o.side == "buy":
            qty_limited = enforce_position_limits(o.ticker, qty_cash_clamped, price, equity, positions_value, settings)
        else:
            owned = 0

            if not df.empty and o.ticker in df["Ticker"].values:
                owned = int(float(df[df["Ticker"] == o.ticker]["Shares"].iloc[0]))

            qty_limited = min(int(o.shares), owned)

        if qty_limited <= 0:
            continue

        value = qty_limited * price

        if o.side == "buy":
            total_new_alloc += value

        symbols_after = set(symbols_before)

        if o.side == "buy":
            symbols_after.add(o.ticker)

        if not within_max_symbols(symbols_after, settings):
            continue

        if not max_daily_allocation_ok(total_new_alloc, equity, settings):
            continue

        validated_orders.append({"ticker": o.ticker, "side": o.side, "shares": qty_limited, "reason": o.reason})

    clock = get_clock(alpaca)

    if not clock.is_open:
        pass

    for vo in validated_orders:
        client_id = make_client_order_id("chatgptbot", vo["ticker"])
        res = execute_trade(alpaca, vo, dry_run=bool(settings["dry_run"]), client_order_id=client_id)

        log = {
            "Timestamp": iso_now_utc(),
            "Date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "Ticker": vo["ticker"],
            "Shares": vo["shares"],
            "Side": vo["side"],
            "Reason": vo.get("reason", ""),
            "OrderStatus": res.get("status", ""),
            "OrderId": res.get("order_id", ""),
            "ClientOrderId": client_id
        }
        save_trade_log(settings["trade_log_csv"], log)

    save_thesis(thesis_path, ai.thesis or "No thesis returned.")
    update_portfolio_totals(alpaca, settings["portfolio_csv"])

    new_equity = load_latest_total_equity(settings["portfolio_csv"])
    print(f"Daily Change: ${new_equity - old_equity:.2f}")

    plot_weekly_performance(settings["portfolio_csv"], settings["plot_dir"], interactive=bool(settings["plot_interactive"]))


if __name__ == "__main__":
    main()
