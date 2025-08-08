import os
import pandas as pd
import matplotlib.pyplot as plt


def plot_weekly_performance(portfolio_csv: str, plot_dir: str, interactive: bool = False) -> str:
    os.makedirs(plot_dir, exist_ok=True)
    df = pd.read_csv(portfolio_csv)
    df = df[df["Ticker"] == "TOTAL"].copy()
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True)
    df = df[df["Timestamp"].dt.dayofweek == 0]
    fig = plt.figure(figsize=(10, 5))
    plt.plot(df["Timestamp"], df["Total Equity"], marker="o", label="ChatGPT Portfolio")
    plt.title("Weekly Portfolio Performance")
    plt.xlabel("Date")
    plt.ylabel("Total Equity ($)")
    plt.xticks(rotation=30)
    plt.grid(True)
    plt.legend()
    path = os.path.join(plot_dir, "weekly_performance.png")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    if interactive:
        plt.show()
    plt.close(fig)
    return path
