import os
import json
import time
import pandas as pd
from typing import Any
from alpaca_trade_api.rest import REST
from dotenv import load_dotenv
import openai

# Load API keys
load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set up clients
alpaca = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
openai.api_key = OPENAI_API_KEY

PORTFOLIO_CSV = "Scripts and CSV Files/chatgpt_portfolio_update.csv"

def load_latest_portfolio_state(file: str) -> tuple[list[dict[str, Any]], float]:
    df = pd.read_csv(file)
    if df.empty:
        raise ValueError("Portfolio CSV is empty.")
    non_total = df[df["Ticker"] != "TOTAL"].copy()
    non_total["Date"] = pd.to_datetime(non_total["Date"])
    latest_date = non_total["Date"].max()
    latest = non_total[non_total["Date"] == latest_date].copy()
    latest.drop(columns=["Date", "Cash Balance", "Total Equity", "Action", "Current Price", "PnL", "Total Value"], inplace=True)
    latest.rename(columns={"Cost Basis": "buy_price", "Shares": "shares", "Ticker": "ticker", "Stop Loss": "stop_loss"}, inplace=True)
    latest["cost_basis"] = latest["shares"] * latest["buy_price"]
    totals = df[df["Ticker"] == "TOTAL"].copy()
    totals["Date"] = pd.to_datetime(totals["Date"])
    cash = float(totals.sort_values("Date").iloc[-1]["Cash Balance"])
    return latest.to_dict(orient="records"), cash

def create_prompt(week: int, day: int, portfolio: list[dict[str, Any]], cash: float, last_thesis: str) -> str:
    return f"""
You are a professional-grade portfolio analyst. You have a portfolio (week {week}, day {day}). Your current portfolio is: {portfolio}, with ${cash:.2f} in cash.
The last analyst had this thesis: "{last_thesis}"

Use deep research to re-evaluate this portfolio. You may buy/sell any U.S.-listed **micro-cap stocks** (market cap < $300M). Use only **full-share positions**, no fractional shares. Use only the cash available.

Output JSON like this:

```json
{{
  "actions": [
    {{
      "action": "sell",
      "ticker": "XYZ",
      "shares": 2,
      "reason": "Downgrade / valuation concerns"
    }},
    {{
      "action": "buy",
      "ticker": "ABC",
      "shares": 3,
      "buy_price": 6.42,
      "stop_loss": 5.48,
      "reason": "Strong outlook / momentum / etc."
    }}
  ],
  "thesis": "Summary for next week."
}}
"""

def call_openai(prompt: str) -> str:
    res = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a professional-grade portfolio strategist."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000,
    )
    return res["choices"][0]["message"]["content"]

def log_manual_buy(portfolio: list[dict], ticker: str, shares: int, price: float, stop_loss: float, cash: float) -> tuple[float, list[dict]]:
    cost = price * shares
    if cost > cash:
        raise ValueError(f"Not enough cash to buy {shares} of {ticker} at ${price}")
    portfolio.append({
        "ticker": ticker,
        "buy_price": price,
        "shares": shares,
        "stop_loss": stop_loss,
        "cost_basis": round(cost, 2)
    })
    return round(cash - cost, 2), portfolio

def log_manual_sell(portfolio: list[dict], ticker: str, shares: int, price: float, cash: float) -> tuple[float, list[dict]]:
    for row in portfolio:
        if row["ticker"] == ticker:
            if shares > row["shares"]:
                raise ValueError(f"Tried to sell more shares than owned for {ticker}")
            row["shares"] -= shares
            row["cost_basis"] = round(row["buy_price"] * row["shares"], 2)
            if row["shares"] == 0:
                portfolio.remove(row)
            return round(cash + price * shares, 2), portfolio
    raise ValueError(f"No holding found for ticker: {ticker}")

def execute_trades(json_str: str, portfolio: list[dict], cash: float) -> tuple[list[dict], float, str]:
    response = json.loads(json_str)
    for action in response["actions"]:
        ticker = action["ticker"]
        if action["action"] == "sell":
            shares = int(action["shares"])
            price = float(alpaca.get_latest_trade(ticker).price)
            print(f"💸 Selling {shares} x {ticker} @ ${price:.2f}")
            cash, portfolio = log_manual_sell(portfolio, ticker, shares, price, cash)
        elif action["action"] == "buy":
            shares = int(action["shares"])
            buy_price = float(action["buy_price"])
            stop_loss = float(action["stop_loss"])
            print(f"🛒 Buying {shares} x {ticker} @ ${buy_price:.2f}")
            cash, portfolio = log_manual_buy(portfolio, ticker, shares, buy_price, stop_loss, cash)
    return portfolio, cash, response["thesis"]

def main():
    week = 6
    day = 3
    last_thesis = "Momentum-based allocation focused on small biotech and tech companies."
    portfolio, cash = load_latest_portfolio_state(PORTFOLIO_CSV)
    prompt = create_prompt(week, day, portfolio, cash, last_thesis)
    print("📤 Sending prompt to OpenAI...")
    response = call_openai(prompt)
    print("📥 GPT response received. Parsing and executing...\n")
    portfolio, cash, thesis = execute_trades(response, portfolio, cash)
    print("\n✅ New portfolio state:")
    print(json.dumps(portfolio, indent=2))
    print(f"\n💰 Cash remaining: ${cash:.2f}")
    print(f"\n🧠 New thesis: {thesis}")

if __name__ == "__main__":
    main()
