import pandas as pd
from typing import Tuple
from .alpaca_service import list_positions, get_account


def load_portfolio(alpaca) -> Tuple[pd.DataFrame, float]:
    positions = list_positions(alpaca)
    rows = []
    for p in positions:
        rows.append({
            "Ticker": p.symbol,
            "Shares": float(p.qty),
            "Cost Basis": float(p.avg_entry_price) if p.avg_entry_price else 0.0,
            "Current Price": float(p.current_price) if hasattr(p, "current_price") else 0.0,
            "Total Value": float(p.market_value) if p.market_value else 0.0
        })
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Ticker","Shares","Cost Basis","Current Price","Total Value"])
    account = get_account(alpaca)
    cash = float(account.cash)
    return df, cash


def summarize_portfolio_for_prompt(df: pd.DataFrame) -> str:
    cols = ["Ticker","Shares","Cost Basis","Current Price","Total Value"]
    if not set(cols).issubset(df.columns):
        return "[]"
    return df.to_json(orient="records")
