import json

from typing import List, Dict


def run_backtest(daily_snapshots: List[Dict], settings: Dict) -> Dict:
    equity = 100000.0
    history = []
    for snap in daily_snapshots:
        eq = snap.get("equity", equity)
        equity = eq
        history.append(eq)
    return {"final_equity": equity, "history": history}
