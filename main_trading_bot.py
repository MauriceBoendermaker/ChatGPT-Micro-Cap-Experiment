import os
import json
import time
import pandas as pd
import matplotlib.pyplot as plt

from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame

# Load .env
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Alpaca
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL")
alpaca = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

# Constants
DATA_DIR = "Scripts and CSV Files"
PORTFOLIO_CSV = f"{DATA_DIR}/chatgpt_portfolio_update.csv"
TRADE_LOG_CSV = f"{DATA_DIR}/chatgpt_trades.csv"

THESIS_FILE = f"{DATA_DIR}/thesis.txt"


# === Thesis Utilities ===

def load_thesis() -> str:
    if os.path.exists(THESIS_FILE):
        with open(THESIS_FILE, "r") as f:
            return f.read().strip()
    return "Initial thesis not available."

def save_thesis(new_thesis: str) -> None:
    with open(THESIS_FILE, "w") as f:
        f.write(new_thesis)


# === Portfolio Functions ===

def load_portfolio():
    df = pd.read_csv(PORTFOLIO_CSV)
    df["Date"] = pd.to_datetime(df["Date"])
    latest_date = df["Date"].max()

    today_df = df[df["Date"] == latest_date]
    holdings = today_df[today_df["Ticker"] != "TOTAL"].copy()
    total_row = today_df[today_df["Ticker"] == "TOTAL"]

    if total_row.empty:
        raise ValueError(f"No TOTAL row found for {latest_date.date()} in portfolio CSV.")

    cash = float(total_row["Cash Balance"].iloc[0])
    return holdings.reset_index(drop=True), cash



def save_trade_log(log: dict):
    if os.path.exists(TRADE_LOG_CSV):
        df = pd.read_csv(TRADE_LOG_CSV)
        df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(TRADE_LOG_CSV, index=False)


# === OpenAI Prompt System ===

def get_portfolio_prompt(portfolio: pd.DataFrame, cash: float, previous_thesis: str, week: int):
    base_prompt = f"""
    You are a professional-grade portfolio strategist. You have a portfolio (currently Week {week}) and these are your holdings:
    
    {portfolio.to_dict(orient="records")}
    
    Cash available: ${cash:.2f}
    
    Here was your previous investment thesis:
    {previous_thesis}
    
    Use deep research to reevaluate the portfolio. Only use U.S.-listed micro-cap stocks with a market cap under $300M.
    
    You may buy or sell any number of shares as long as there is enough cash.
    
    ⚠️ Return your response as a **valid JSON object**, using the following format (all keys must be lowercase):
    
    ```json
    {{
      "orders": [
        {{"ticker": "XYZ", "side": "buy", "shares": 10, "reason": "Short-term catalyst"}}
      ],
      "thesis": "Rewritten investment thesis here"
    }}
    ```
    """
    return base_prompt.strip()

def ask_openai(prompt: str) -> dict:
    print("Requesting new trading decisions from OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    reply = response.choices[0].message.content

    print("🧠 Raw OpenAI reply:\n", reply)

    try:
        json_part = reply.split("```json")[1].split("```")[0].strip()
        return json.loads(json_part)
    except Exception as e:
        print(f"⚠️ Could not parse response:\n{reply}")
        raise e


# === Alpaca Execution ===

def execute_trade(order: dict, dry_run: bool = False):
    side = order["side"]
    symbol = order["ticker"]
    qty = int(order["shares"])
    reason = order.get("reason", "AUTO TRADE")

    if dry_run:
        print(f"[DRY RUN] Would {side} {qty} shares of {symbol}")
        return True

    # Check if enough shares exist before submitting a sell
    if side == "sell":
        positions = {p.symbol: int(float(p.qty)) for p in alpaca.list_positions()}
        owned_qty = positions.get(symbol, 0)
        if owned_qty <= 0 or qty > owned_qty:
            print(f"❌ SKIPPING: Tried to sell {qty} of {symbol}, but you only own {owned_qty}")
            return False  # Don't allow shorting

    try:
        alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="day"
        )
        print(f"✅ {side.upper()} {qty} x {symbol} - Reason: {reason}")
        return True
    except Exception as e:
        print(f"🚨 Error placing order for {symbol}: {e}")
        return False


# === Visualization ===

def plot_weekly_performance():
    df = pd.read_csv(PORTFOLIO_CSV)
    df = df[df["Ticker"] == "TOTAL"]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[df["Date"].dt.dayofweek == 0]  # Mondays

    plt.figure(figsize=(10, 5))
    plt.plot(df["Date"], df["Total Equity"], marker="o", label="ChatGPT Portfolio")
    plt.title("Weekly Portfolio Performance")
    plt.xlabel("Date")
    plt.ylabel("Total Equity ($)")
    plt.xticks(rotation=30)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


def update_portfolio_totals():
    account = alpaca.get_account()
    date = datetime.now().strftime("%Y-%m-%d")
    total_equity = float(account.equity)
    cash_balance = float(account.cash)

    new_row = {
        "Date": date,
        "Ticker": "TOTAL",
        "Shares": "",
        "Cost Basis": "",
        "Stop Loss": "",
        "Current Price": "",
        "Total Value": 0.0,
        "PnL": 0.0,
        "Action": "",
        "Cash Balance": cash_balance,
        "Total Equity": total_equity
    }

    if os.path.exists(PORTFOLIO_CSV):
        df = pd.read_csv(PORTFOLIO_CSV)
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        df = pd.DataFrame([new_row])

    df.to_csv(PORTFOLIO_CSV, index=False)


def load_latest_total_equity():
    if not os.path.exists(PORTFOLIO_CSV):
        return 0
    df = pd.read_csv(PORTFOLIO_CSV)
    df = df[df["Ticker"] == "TOTAL"]
    if df.empty:
        return 0
    return float(df["Total Equity"].iloc[-1])


# === Main Logic ===

def main():
    print(f"🔁 Running ChatGPT Micro-Cap Trading Bot: {datetime.now().strftime('%Y-%m-%d')}")

    # Step 1: Capture equity BEFORE making trades
    old_equity = load_latest_total_equity()

    # Step 2: Load current portfolio + cash
    portfolio, cash = load_portfolio()
    last_thesis = load_thesis()

    # Step 3: Get AI response
    prompt = get_portfolio_prompt(portfolio, cash, last_thesis, week=6)
    ai_response = ask_openai(prompt)

    # Step 4: Parse AI output
    if isinstance(ai_response, list):
        orders = ai_response
        new_thesis = "No thesis provided."
    elif isinstance(ai_response, dict):
        orders = ai_response.get("orders", [])
        new_thesis = ai_response.get("thesis", "No thesis returned.")
    else:
        raise ValueError("Unexpected response format from OpenAI.")

    # Step 5: Execute trades
    for order in orders:
        result = execute_trade(order, dry_run=False)
        if not result:
            continue

        log_entry = {
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Ticker": order["ticker"],
            "Shares": order["shares"],
            "Side": order["side"],
            "Reason": order.get("reason", "Auto decision"),
        }
        save_trade_log(log_entry)

    # Step 6: Update thesis and portfolio totals
    save_thesis(new_thesis)
    update_portfolio_totals()

    # Step 7: Capture equity AFTER trades
    new_equity = load_latest_total_equity()

    # Step 8: Print result
    print(f"📊 Daily Change: ${new_equity - old_equity:.2f}")
    print(f"\n📈 New Thesis:\n{new_thesis}")
    plot_weekly_performance()



if __name__ == "__main__":
    main()
