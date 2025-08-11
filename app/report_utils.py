import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from datetime import datetime, timezone


def load_inception_equity(portfolio_csv: str) -> float:
    if not os.path.exists(portfolio_csv):
        return 0.0
    df = pd.read_csv(portfolio_csv)
    df = df[df["Ticker"] == "TOTAL"].copy()
    if df.empty:
        return 0.0
    try:
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.sort_values("Date")
        return float(df["Total Equity"].iloc[0])
    except Exception:
        return float(df["Total Equity"].head(1).astype(float).values[0])


def save_equity_chart(portfolio_csv: str, plot_dir: str) -> str:
    os.makedirs(plot_dir, exist_ok=True)
    df = pd.read_csv(portfolio_csv)
    df = df[df["Ticker"] == "TOTAL"].copy()
    if df.empty:
        return ""
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date")
        x = df["Date"]
    else:
        x = range(len(df))
    p = os.path.join(plot_dir, f"equity_{datetime.now(timezone.utc).strftime('%Y%m%d')}.png")
    plt.figure(figsize=(7.5, 3.6))
    plt.plot(x, df["Total Equity"], marker="o")
    ax = plt.gca()
    ax.set_title("Portfolio Equity")
    ax.set_xlabel("Date")
    ax.set_ylabel("USD")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"${y:,.0f}"))
    ax.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(p, dpi=160)
    plt.close()
    return p


def save_pnl_chart(portfolio_csv: str, plot_dir: str) -> str:
    os.makedirs(plot_dir, exist_ok=True)
    df = pd.read_csv(portfolio_csv)
    df = df[df["Ticker"] == "TOTAL"].copy()
    if df.empty:
        return ""
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date")
        x = df["Date"]
    else:
        x = range(len(df))
    start_eq = float(df["Total Equity"].iloc[0])
    pnl = df["Total Equity"].astype(float) - start_eq
    p = os.path.join(plot_dir, f"pnl_{datetime.now(timezone.utc).strftime('%Y%m%d')}.png")
    plt.figure(figsize=(7.5, 2.6))
    plt.plot(x, pnl, marker="o")
    ax = plt.gca()
    ax.set_title("Cumulative P/L")
    ax.set_xlabel("Date")
    ax.set_ylabel("USD")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"${y:,.0f}"))
    ax.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(p, dpi=160)
    plt.close()
    return p


def write_csv_snapshots(positions_df: pd.DataFrame, trades_today: list, out_dir: str) -> list:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    paths = []
    pos_path = os.path.join(out_dir, f"positions_{ts}.csv")
    trades_path = os.path.join(out_dir, f"trades_{ts}.csv")
    if positions_df is not None:
        positions_df.to_csv(pos_path, index=False)
        paths.append(pos_path)
    _df = pd.DataFrame(trades_today or [])
    _df.to_csv(trades_path, index=False)
    paths.append(trades_path)
    return paths


def compute_risk_alerts(positions_df, equity_val: float, settings: dict, sectors_by_ticker: dict):
    alerts = {"positions": [], "sectors": []}
    if positions_df is None or positions_df.empty or equity_val <= 0:
        return alerts
    pos_limit = float(settings.get("risk", {}).get("max_pos_pct_of_equity", 0.10))
    sector_limit = float(settings.get("risk", {}).get("max_sector_pct_of_equity", 0.30))
    rows = []
    for _, r in positions_df.iterrows():
        ticker = str(r["Ticker"])
        val = float(r.get("Total Value", 0.0))
        pct = val / equity_val if equity_val else 0.0
        sector = sectors_by_ticker.get(ticker, "Unknown")
        rows.append((ticker, sector, val, pct))
        if pct > pos_limit:
            alerts["positions"].append(f"{ticker} is {pct:.1%} of equity (${val:,.0f}) — limit {pos_limit:.0%}")
    from collections import defaultdict
    sector_sum = defaultdict(float)
    for _, sector, val, _ in rows:
        sector_sum[sector] += val
    for sector, sval in sector_sum.items():
        spct = sval / equity_val if equity_val else 0.0
        if spct > sector_limit:
            alerts["sectors"].append(f"{sector} is {spct:.1%} of equity (${sval:,.0f}) — limit {sector_limit:.0%}")
    return alerts
