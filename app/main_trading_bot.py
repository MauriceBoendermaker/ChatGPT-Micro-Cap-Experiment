import os
import time
import random

from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from datetime import datetime, timezone

from .config_loader import load_settings
from .thesis import load_thesis, save_thesis
from .alpaca_service import make_alpaca, get_account, get_clock, submit_order, get_order
from .market_data import enrich_symbol
from .risk_engine import validate_symbol, make_client_order_id
from .openai_agent import get_portfolio_prompt, ask_openai
from .plotting import plot_weekly_performance
from .storage import save_trade_log, append_total_row, load_latest_total_equity, iso_now_utc
from .portfolio import load_portfolio, summarize_portfolio_for_prompt
from .universe_builder import auto_universe
from .risk_controls import breached_daily_drawdown, flatten_all, make_bracket_kwargs
from .db import init_db, insert_trade
from .market_health import market_is_healthy
from .thesis_change import thesis_changed
from .multi_model_voter import vote_orders
from .budget_rebalancer import rebalance, save_virtual_equity
from .state import load_state, save_state
from .market_forecast import next_day_forecast
from .reporter import build_report_html, send_email_html
from .report_utils import save_equity_chart, save_pnl_chart, write_csv_snapshots, compute_risk_alerts, load_inception_equity
from .site_publisher import publish_dashboard



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
        if s.status in {"filled", "canceled", "rejected", "partially_filled", "expired"}:
            return {
                "status": s.status,
                "symbol": symbol,
                "side": side,
                "qty": float(s.filled_qty or 0),
                "order_id": oid,
                "reason": reason,
                "filled_avg_price": float(getattr(s, "filled_avg_price", 0) or 0)
            }
    s = get_order(alpaca, oid)
    return {
        "status": s.status,
        "symbol": symbol,
        "side": side,
        "qty": float(s.filled_qty or 0),
        "order_id": oid,
        "reason": reason,
        "filled_avg_price": float(getattr(s, "filled_avg_price", 0) or 0)
    }


def _local_timestamp_and_subject(tz_name: str = "Europe/Amsterdam"):
    now_local = datetime.now(ZoneInfo(tz_name))
    as_of_str = now_local.strftime("%A, %d %b %Y %H:%M %Z")
    subject = f"Daily Trading Report - {now_local.strftime('%A')}"
    return as_of_str, subject


def _intraday_unrealized_pl(alpaca) -> float:
    try:
        total = 0.0
        for p in alpaca.list_positions():
            val = getattr(p, "unrealized_intraday_pl", None)
            if val is not None:
                total += float(val)
        return total
    except Exception:
        return 0.0


def _total_unrealized_pl(alpaca) -> float:
    try:
        s = 0.0
        for p in alpaca.list_positions():
            v = getattr(p, "unrealized_pl", None)
            if v is not None:
                s += float(v)
        return s
    except Exception:
        return 0.0


def _top_and_worst_today(alpaca):
    try:
        items = []
        for p in alpaca.list_positions():
            sym = getattr(p, "symbol", "")
            pc = getattr(p, "unrealized_intraday_plpc", None)
            try:
                pct = float(pc) if pc is not None else 0.0
            except Exception:
                pct = 0.0
            items.append((sym, pct))
        if not items:
            return None, None
        top = max(items, key=lambda x: x[1])
        worst = min(items, key=lambda x: x[1])
        return top, worst
    except Exception:
        return None, None


def _fill_spread_candidates(alpaca, uni_syms, df, existing, target_count, settings):
    have = {c["ticker"] for c in existing}
    held = set(df["Ticker"].astype(str).tolist()) if df is not None and not df.empty else set()
    pool = [s for s in uni_syms if s not in have and s not in held]
    random.shuffle(pool)
    out = list(existing)
    for sym in pool:
        if len(out) >= target_count:
            break
        try:
            meta = enrich_symbol(alpaca, sym)
            if not validate_symbol(meta, settings):
                continue
            price = float(meta["price"])
            if price <= 0:
                continue
            out.append({"ticker": sym, "price": price, "reason": "SPREAD_FILL"})
        except Exception:
            continue
    return out


def send_daily_report(alpaca, df, ai_thesis, trades_today, port_json, settings, state, state_path):
    acct = get_account(alpaca)
    tz = settings.get("timezone", "Europe/Amsterdam")
    from zoneinfo import ZoneInfo
    today_local = datetime.now(ZoneInfo(tz)).date()
    if state.get("daily_baseline_date") != str(today_local):
        state["daily_baseline_date"] = str(today_local)
        state["daily_baseline_equity"] = float(acct.equity)
        save_state(state_path, state)
    equity_val = float(acct.equity)
    cash_val = float(acct.cash)
    baseline = float(state.get("daily_baseline_equity", equity_val))
    daily_pnl = equity_val - baseline
    as_of_iso, subject = _local_timestamp_and_subject(tz)
    eq_path = save_equity_chart(settings["portfolio_csv"], settings["plot_dir"])
    pnl_path = save_pnl_chart(settings["portfolio_csv"], settings["plot_dir"])
    tickers = df["Ticker"].astype(str).tolist() if df is not None and not df.empty else []
    sectors = {}
    for sym in tickers:
        try:
            meta = enrich_symbol(alpaca, sym)
            sectors[sym] = meta.get("sector", "Unknown")
        except Exception:
            sectors[sym] = "Unknown"
    alerts = compute_risk_alerts(df, equity_val, settings, sectors)
    attachments = write_csv_snapshots(df, trades_today, settings.get("report_dir", settings["plot_dir"]))
    vote_summary = "Multi-model voting enabled" if settings.get("vote", {}).get("enabled", True) else ""
    intraday_pl = _intraday_unrealized_pl(alpaca)
    vote_summary = (vote_summary + f" • Intraday UPL: ${intraday_pl:,.2f}").strip(" •")
    inception_eq = load_inception_equity(settings["portfolio_csv"])
    total_pl = float(equity_val) - float(inception_eq)
    top, worst = _top_and_worst_today(alpaca)

    inline_images = {}
    inline_cid = None
    pnl_cid = None

    if eq_path and os.path.exists(eq_path):
        inline_images["chart"] = eq_path
        inline_cid = "chart"

    if pnl_path and os.path.exists(pnl_path):
        inline_images["pnl"] = pnl_path
        pnl_cid = "pnl"

    html = build_report_html(
        trades_today=trades_today,
        positions_df=df,
        thesis=ai_thesis,
        forecast=next_day_forecast(f"Holdings JSON: {port_json}\nThesis: {ai_thesis}"),
        equity=equity_val,
        cash=cash_val,
        daily_pnl=daily_pnl,
        as_of_iso=as_of_iso,
        vote_summary=vote_summary,
        inline_cid=inline_cid,
        pnl_cid=pnl_cid,
        total_pl=total_pl,
        risk_alerts=alerts,
        news_by_ticker=None,
        top_performer=top,
        worst_performer=worst
    )

    try:
        publish_dashboard(
            html,
            inline_images,
            attachments,
            settings,
            equity_val,
            cash_val,
            daily_pnl,
            total_pl,
            as_of_iso
        )
    except Exception as e:
        print("Dashboard publish failed:", repr(e))

    send_email_html(subject, html, inline_images, attachments)


def main():
    cutoff = os.getenv("RUN_UNTIL")  # e.g., 2025-09-01
    if cutoff:
        today = datetime.utcnow().date()
        if today > datetime.strptime(cutoff, "%Y-%m-%d").date():
            return

    init_db()
    load_dotenv()
    settings_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")
    settings = load_settings(settings_path)
    alpaca = make_alpaca()

    old_equity = load_latest_total_equity(settings["portfolio_csv"])
    start_equity_today = float(get_account(alpaca).equity)

    df, cash_live = load_portfolio(alpaca)
    thesis_path = settings["thesis_file"]
    last_thesis = load_thesis(thesis_path)
    port_json = summarize_portfolio_for_prompt(df)

    state_path = settings.get("state_file", os.path.join(os.path.dirname(__file__), "state.json"))
    state = load_state(state_path)

    try:
        uni_syms = auto_universe(alpaca, settings)
        if uni_syms:
            state["last_universe"] = uni_syms
            save_state(state_path, state)
    except Exception:
        uni_syms = state.get("last_universe", [])
        if not uni_syms:
            uni_syms = ["ABEO", "ADMA", "SLS", "TRVN", "CRMD", "CTXR"]

    base_prompt = get_portfolio_prompt(port_json, cash_live, last_thesis, week=6) + f" Only choose from: {uni_syms[:50]}"
    if settings.get("vote", {}).get("enabled", True):
        voted_orders, voted_thesis = vote_orders(base_prompt, settings)
        class _Tmp: pass
        ai = _Tmp()
        ai.orders = []
        for o in voted_orders:
            ai.orders.append(type("O", (object,), o))
        ai.thesis = voted_thesis
    else:
        ai = ask_openai(base_prompt)

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
        send_daily_report(alpaca, df, ai.thesis, [], port_json, settings, state, state_path)
        plot_weekly_performance(settings["portfolio_csv"], settings["plot_dir"], interactive=bool(settings["plot_interactive"]))
        return

    healthy = market_is_healthy(alpaca)

    budget = settings.get("budget", {})
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

    target_positions = int(settings.get("spread", {}).get("target_positions", 4))
    if healthy and settings.get("spread", {}).get("enabled", True):
        buy_candidates = _fill_spread_candidates(alpaca, uni_syms, df, buy_candidates, target_positions, settings)

    buy_candidates = buy_candidates[:max(int(settings.get("risk", {}).get("max_symbols", target_positions)), target_positions)]

    remaining = float(settings["budget"]["max_daily_allocation_abs"])
    intended_n = max(1, min(len(buy_candidates), target_positions))
    per_name = remaining / intended_n if buy_candidates else 0.0

    validated_orders = []
    for c in buy_candidates[:intended_n]:
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
        send_daily_report(alpaca, df, ai.thesis, [], port_json, settings, state, state_path)
        return

    clock = get_clock(alpaca)
    place_when_closed = bool(settings.get("trade_timing", {}).get("place_when_market_closed", True))

    if clock.is_open:
        pass
    else:
        if place_when_closed:
            print("Market closed; will queue DAY orders for next session.")
        else:
            print("Market closed and placing-when-closed disabled; skipping order placement.")
            validated_orders = []

    trades_today = []
    for vo in validated_orders:
        client_id = make_client_order_id("chatgptbot", vo["ticker"])
        res = execute_trade(alpaca, vo, limit_price=vo["limit_price"], settings=settings, dry_run=bool(settings["dry_run"]), client_order_id=client_id)
        trades_today.append({
            "Timestamp": iso_now_utc(),
            "Date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "Ticker": vo["ticker"],
            "Shares": vo["shares"],
            "Side": vo["side"],
            "OrderStatus": res.get("status", ""),
            "OrderId": res.get("order_id", "")
        })
        insert_trade(vo["ticker"], vo["side"], int(vo["shares"]), float(vo["limit_price"]), res.get("status", ""), int(res.get("qty", 0)), float(res.get("filled_avg_price", vo["limit_price"])))
        save_trade_log(settings["trade_log_csv"], trades_today[-1])

    save_thesis(thesis_path, ai.thesis or "No thesis returned.")
    update_portfolio_totals(alpaca, settings["portfolio_csv"])

    new_equity = load_latest_total_equity(settings["portfolio_csv"])

    state_path = settings.get("state_file", os.path.join(os.path.dirname(__file__), "state.json"))
    state = load_state(state_path)
    base_eq = float(state.get("base_equity", new_equity))
    new_virtual, changed = rebalance(float(settings["budget"]["virtual_equity"]), base_eq, new_equity, settings)
    if changed:
        save_virtual_equity(settings_path, settings, new_virtual)

    send_daily_report(alpaca, df, ai.thesis, trades_today, port_json, settings, state, state_path)

    state["base_equity"] = new_equity
    save_state(state_path, state)

    if old_equity == 0:
        print("Baseline set. Daily Change will be meaningful from next run.")
    else:
        print(f"Daily Change: ${new_equity - old_equity:.2f}")

    plot_weekly_performance(settings["portfolio_csv"], settings["plot_dir"], interactive=bool(settings["plot_interactive"]))


if __name__ == "__main__":
    main()
    print("Summary email sent.")
