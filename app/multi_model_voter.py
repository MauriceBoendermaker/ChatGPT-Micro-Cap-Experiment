import json

from collections import defaultdict
from typing import List, Dict, Tuple
from openai import OpenAI
from .schemas import AIResponse


def _ask(model: str, prompt: str) -> AIResponse:
    c = OpenAI()
    r = c.chat.completions.create(model=model, response_format={"type":"json_object"}, temperature=0.2, messages=[{"role":"user","content":prompt}])
    data = json.loads(r.choices[0].message.content)
    return AIResponse(**data)


def vote_orders(prompt: str, settings: dict) -> Tuple[List[Dict], str]:
    models = settings.get("vote", {}).get("models", ["gpt-4o"])
    min_votes = int(settings.get("vote", {}).get("min_votes", 2))
    ballots = []
    theses = []

    for m in models:
        a = _ask(m, prompt)
        theses.append(a.thesis or "")
        rows = []

        for o in a.orders:
            rows.append({"ticker": o.ticker.upper(), "side": o.side.lower(), "shares": float(o.shares), "reason": o.reason})
        ballots.append(rows)

    counts = defaultdict(int)
    reasons = defaultdict(list)

    for rows in ballots:
        seen = set()

        for o in rows:
            key = (o["ticker"], o["side"])

            if key in seen:
                continue

            seen.add(key)
            counts[key] += 1
            reasons[key].append(o.get("reason",""))

    agreed = []

    for key, v in counts.items():
        if v >= min_votes:
            t, s = key
            agreed.append({"ticker": t, "side": s, "shares": 100, "reason": " | ".join(reasons[key])[:500]})

    thesis = max(theses, key=lambda x: len(x)) if theses else ""
    return agreed, thesis
