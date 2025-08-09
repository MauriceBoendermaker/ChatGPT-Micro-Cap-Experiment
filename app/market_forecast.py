import json

from openai import OpenAI


def next_day_forecast(prompt_context: str) -> str:
    c = OpenAI()
    r = c.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type":"text"},
        temperature=0.4,
        messages=[{"role":"user","content":f"Given this portfolio and thesis, write a 3-bullet cautious forecast for tomorrow:\n{prompt_context}"}]
    )
    return r.choices[0].message.content.strip()
