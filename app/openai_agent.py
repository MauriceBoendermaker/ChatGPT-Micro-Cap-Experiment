import os
import json

from openai import OpenAI
from .schemas import AIResponse


def get_portfolio_prompt(portfolio_summary_json: str, cash: float, previous_thesis: str, week: int) -> str:
    return (
        f"You are a professional-grade portfolio strategist. You have a portfolio (Week {week}). "
        f"Holdings: {portfolio_summary_json} "
        f"Cash: {cash:.2f} "
        f"Previous thesis: {previous_thesis} "
        f"Only use U.S.-listed micro-cap stocks with market cap under $300M, price >= $1, and sufficient liquidity. "
        f"Return a JSON object with lowercase keys: "
        f'{{"orders":[{{"ticker":"XYZ","side":"buy","shares":10,"reason":"r"}}], "thesis":"t"}} '
        f"Do not include commentary."
    )


def ask_openai(prompt: str) -> AIResponse:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    r = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    content = r.choices[0].message.content
    data = json.loads(content)
    return AIResponse(**data)
