"""
Alpha Vantage technical indicators — RSI, MACD, Bollinger Bands.
Requires ALPHA_VANTAGE_KEY in .streamlit/secrets.toml or env.
Free tier: 25 requests/day.
"""
import streamlit as st
import requests
import pandas as pd

_BASE = "https://www.alphavantage.co/query"


def _get_key() -> str | None:
    try:
        return st.secrets["ALPHA_VANTAGE_KEY"]
    except Exception:
        import os
        return os.environ.get("ALPHA_VANTAGE_KEY")


def _fetch(params: dict) -> dict:
    key = _get_key()
    if not key:
        return {}
    try:
        r = requests.get(_BASE, params={**params, "apikey": key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_rsi(ticker: str, interval: str = "daily", period: int = 14) -> pd.Series:
    data = _fetch({
        "function":    "RSI",
        "symbol":      ticker,
        "interval":    interval,
        "time_period": period,
        "series_type": "close",
    })
    raw = data.get(f"Technical Analysis: RSI", {})
    if not raw:
        return pd.Series(dtype=float)
    s = pd.Series({d: float(v["RSI"]) for d, v in raw.items()}, dtype=float)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_macd(ticker: str, interval: str = "daily") -> pd.DataFrame:
    data = _fetch({
        "function":          "MACD",
        "symbol":            ticker,
        "interval":          interval,
        "series_type":       "close",
    })
    raw = data.get("Technical Analysis: MACD", {})
    if not raw:
        return pd.DataFrame()
    rows = {d: {k: float(v) for k, v in vals.items()} for d, vals in raw.items()}
    df = pd.DataFrame(rows).T
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bbands(ticker: str, interval: str = "daily", period: int = 20) -> pd.DataFrame:
    data = _fetch({
        "function":    "BBANDS",
        "symbol":      ticker,
        "interval":    interval,
        "time_period": period,
        "series_type": "close",
    })
    raw = data.get("Technical Analysis: BBANDS", {})
    if not raw:
        return pd.DataFrame()
    rows = {d: {k: float(v) for k, v in vals.items()} for d, vals in raw.items()}
    df = pd.DataFrame(rows).T
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def technical_available() -> bool:
    return bool(_get_key())
