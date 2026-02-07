import ccxt
import pandas as pd
import ta
import numpy as np
from fastapi import FastAPI
from datetime import datetime

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

exchange = ccxt.binance()

SYMBOL = "ETH/USDT"
TIMEFRAME = "15m"
LIMIT = 120

LAST_SIGNAL = "WAIT"

# ---------------- DATA ----------------
def get_data():
    bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(
        bars, columns=["time", "open", "high", "low", "close", "volume"]
    )
    return df

# ---------------- INDICATORS ----------------
def add_indicators(df):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()

    bb = ta.volatility.BollingerBands(df["close"])
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()
    df["bb_width"] = df["bb_high"] - df["bb_low"]

    return df

# ---------------- SUPPORT / RESISTANCE ----------------
def support_resistance(df, lookback=20):
    support = df["low"].rolling(lookback).min().iloc[-2]
    resistance = df["high"].rolling(lookback).max().iloc[-2]
    return round(support, 2), round(resistance, 2)

# ---------------- OI MODULE ----------------
def get_oi_bias():
    # Placeholder – safe, architecture-ready
    return {
        "oi_trend": "Increasing",
        "oi_bias": "Bearish"
    }

# ---------------- SIGNAL ENGINE (CANDLE CLOSE ONLY) ----------------
def generate_signal(df):
    candle = df.iloc[-2]  # CLOSED candle only

    price = candle["close"]
    rsi = candle["rsi"]

    bb_width_now = candle["bb_width"]
    bb_width_prev = df["bb_width"].iloc[-7]

    support, resistance = support_resistance(df)
    oi_data = get_oi_bias()   # 👈 OI fetched HERE

    trend = "Sideways"
    signal = "WAIT"
    confidence = 50

    # SELL
    if (
        price < support
        and rsi < 45
        and bb_width_now > bb_width_prev
        and oi_data["oi_bias"] == "Bearish"
    ):
        signal = "SELL"
        trend = "Bearish"
        confidence = 85

    # BUY
    elif (
        price > resistance
        and rsi > 60
        and bb_width_now > bb_width_prev
        and oi_data["oi_bias"] == "Bullish"
    ):
        signal = "BUY"
        trend = "Bullish"
        confidence = 85

    # 🔑 OI fields are ADDED TO RESULT HERE
    return {
        "symbol": "ETHUSDT",
        "price": round(price, 2),
        "rsi": round(rsi, 2),
        "support": support,
        "resistance": resistance,
        "trend": trend,
        "signal": signal,
        "confidence": confidence,
        "oi_bias": oi_data["oi_bias"],
        "oi_trend": oi_data["oi_trend"]
    }

# ---------------- API ----------------
@app.get("/analysis")
def analysis():
    global LAST_SIGNAL

    try:
        df = get_data()
        df = add_indicators(df)

        # generate_signal already contains OI
        result = generate_signal(df)

        # -------- TIME FILTER (9 AM – 11 PM IST) --------
        hour = datetime.now().hour
        if hour < 9 or hour > 23:
            result["alert"] = False
            result["signal"] = "WAIT"
            return result

        # -------- ALERT ONLY ON NEW BUY / SELL --------
        alert = False
        if result["signal"] in ["BUY", "SELL"] and result["signal"] != LAST_SIGNAL:
            alert = True
            LAST_SIGNAL = result["signal"]

        result["alert"] = alert
        return result

    except Exception as e:
        return {
            "error": str(e)
        }
