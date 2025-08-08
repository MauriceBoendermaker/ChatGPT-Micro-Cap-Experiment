import os
import sqlite3

from datetime import datetime, timezone


DB_PATH = os.path.join(os.path.dirname(__file__), "trades.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ticker TEXT,
        side TEXT,
        qty INTEGER,
        limit_price REAL,
        filled_qty INTEGER,
        filled_avg_price REAL,
        status TEXT,
        pnl REAL
    )
    """)
    conn.commit()
    conn.close()


def insert_trade(ticker, side, qty, limit_price, status, filled_qty=0, filled_avg_price=0.0, pnl=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO trades (timestamp, ticker, side, qty, limit_price, filled_qty, filled_avg_price, status, pnl)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        ticker,
        side,
        qty,
        limit_price,
        filled_qty,
        filled_avg_price,
        status,
        pnl
    ))
    conn.commit()
    conn.close()


def update_trade_pnl(ticker, pnl):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    UPDATE trades SET pnl=? WHERE ticker=? AND pnl IS NULL
    """, (pnl, ticker))
    conn.commit()
    conn.close()


def get_open_trades():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE status NOT IN ('closed','canceled','rejected')")
    rows = c.fetchall()
    conn.close()
    return rows
