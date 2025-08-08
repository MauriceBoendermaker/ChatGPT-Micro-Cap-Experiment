import os
import json
import tempfile
import pandas as pd

from typing import Dict, Any
from datetime import datetime, timezone


COLUMNS = ["Timestamp","Date","Ticker","Shares","Cost Basis","Stop Loss","Current Price","Total Value","PnL","Action","Cash Balance","Total Equity"]


def iso_now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_csv(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=os.path.dirname(path))
    os.close(fd)
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def save_trade_log(path: str, log: Dict[str, Any]) -> None:
    if os.path.exists(path) and os.path.getsize(path) > 0:
        df = pd.read_csv(path)
    else:
        df = pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    _atomic_write_csv(df, path)


def load_latest_total_equity(path: str) -> float:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return 0.0
    df = pd.read_csv(path)
    if "Ticker" not in df.columns or df.empty:
        return 0.0
    df = df[df["Ticker"] == "TOTAL"]
    if df.empty:
        return 0.0
    return float(df["Total Equity"].iloc[-1])


def append_total_row(path: str, row: Dict[str, Any]) -> None:
    if os.path.exists(path) and os.path.getsize(path) > 0:
        df = pd.read_csv(path)
        missing = [c for c in COLUMNS if c not in df.columns]
        for c in missing:
            df[c] = ""
        df = df[COLUMNS]
        df.loc[len(df)] = [row.get(c, "") for c in COLUMNS]
    else:
        df = pd.DataFrame(columns=COLUMNS)
        df.loc[0] = [row.get(c, "") for c in COLUMNS]
    _atomic_write_csv(df, path)