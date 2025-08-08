"""Plot ChatGPT portfolio performance against the S&P 500 (via SPY ETF).

The script loads logged portfolio equity, fetches SPY data from Alpaca,
and renders a comparison chart. Core behaviour remains unchanged;
yFinance has been fully removed.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame

# Load environment variables from .env file
load_dotenv()

# Alpaca config (paper trading)
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)

# File paths
DATA_DIR = "Scripts and CSV Files"
PORTFOLIO_CSV = f"{DATA_DIR}/chatgpt_portfolio_update.csv"

def load_portfolio_totals() -> pd.DataFrame:
    """Load portfolio equity history including a baseline row."""
    chatgpt_df = pd.read_csv(PORTFOLIO_CSV)
    chatgpt_totals = chatgpt_df[chatgpt_df["Ticker"] == "TOTAL"].copy()
    chatgpt_totals["Date"] = pd.to_datetime(chatgpt_totals["Date"])

    baseline_date = pd.Timestamp("2025-08-06")
    baseline_equity = 100
    baseline_row = pd.DataFrame({"Date": [baseline_date], "Total Equity": [baseline_equity]})
    return pd.concat([baseline_row, chatgpt_totals], ignore_index=True).sort_values("Date")


def download_spy(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """Download SPY (S&P 500 ETF) and normalize to $100 baseline."""
    bars = api.get_bars("SPY", TimeFrame.Day, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
    df = bars.df[bars.df["symbol"] == "SPY"].copy().reset_index()

    if df.empty:
        raise ValueError("No SPY data returned from Alpaca.")

    df["Date"] = pd.to_datetime(df["timestamp"]).dt.date
    df["Date"] = pd.to_datetime(df["Date"])  # Ensure pandas datetime format
    df = df.sort_values("Date").reset_index(drop=True)

    spy_baseline_price = df.iloc[0]["close"]
    df["SPX Value ($100 Invested)"] = (df["close"] / spy_baseline_price) * 100
    return df


def main() -> None:
    """Generate and display the performance comparison graph."""
    chatgpt_totals = load_portfolio_totals()
    start_date = pd.Timestamp("2025-08-06")
    end_date = chatgpt_totals["Date"].max()

    spy_data = download_spy(start_date, end_date)

    plt.figure(figsize=(10, 6))
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.plot(
        chatgpt_totals["Date"],
        chatgpt_totals["Total Equity"],
        label="ChatGPT ($100 Invested)",
        marker="o",
        color="blue",
        linewidth=2,
    )
    plt.plot(
        spy_data["Date"],
        spy_data["SPX Value ($100 Invested)"],
        label="S&P 500 via SPY ($100 Invested)",
        marker="o",
        color="orange",
        linestyle="--",
        linewidth=2,
    )

    final_date = chatgpt_totals["Date"].iloc[-1]
    final_chatgpt = float(chatgpt_totals["Total Equity"].iloc[-1])
    final_spx = spy_data["SPX Value ($100 Invested)"].iloc[-1]

    plt.text(final_date, final_chatgpt + 0.3, f"+{final_chatgpt - 100:.1f}%", color="blue", fontsize=9)
    plt.text(final_date, final_spx + 0.9, f"+{final_spx - 100:.1f}%", color="orange", fontsize=9)

    plt.title("ChatGPT's Micro Cap Portfolio vs. S&P 500 (via SPY)")
    plt.xlabel("Date")
    plt.ylabel("Value of $100 Investment")
    plt.xticks(rotation=15)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
