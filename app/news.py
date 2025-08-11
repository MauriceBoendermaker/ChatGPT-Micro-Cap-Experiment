from typing import Dict, List

def fetch_news(alpaca, symbols: List[str], per_symbol: int = 3) -> Dict[str, List[dict]]:
    out = {}
    try:
        for sym in symbols:
            try:
                items = alpaca.get_news(sym, limit=per_symbol)
            except Exception:
                items = []
            rows = []
            for it in items or []:
                rows.append({
                    "headline": getattr(it, "headline", "") or "",
                    "url": getattr(it, "url", "") or "",
                    "source": getattr(it, "source", "") or "",
                    "created_at": str(getattr(it, "created_at", "")) or ""
                })
            out[sym] = rows
    except Exception:
        pass
    return out
