import os
import json
import tempfile
import pandas as pd

from datetime import datetime, timezone
from typing import Dict, Any


def _atomic_write_csv(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=os.path.dirname(path))
    os.close(fd)
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def save_trade_log(path: str, log: Dict[str, Any]) -> None:
    if os.path.exists(path):
        df = pd.read_csv(path)
        df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    _atomic_write_csv(df, path)


def load_latest_total_equity(path: str) -> float:
    if not os.path.exists(path):
        return 0.0
    df = pd.read_csv(path)
    if "Ticker" not in df.columns or df.empty:
        return 0.0
    df = df[df["Ticker"] == "TOTAL"]
    if df.empty:
        return 0.0
    return float(df["Total Equity"].iloc[-1])


def append_total_row(path: str, row: Dict[str, Any]) -> None:
    if os.path.exists(path):
        df = pd.read_csv(path)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    _atomic_write_csv(df, path)


def iso_now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
