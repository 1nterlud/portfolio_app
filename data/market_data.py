import streamlit as st
import yfinance as yf
import pandas as pd
from config import CACHE_TTL


@st.cache_data(ttl=CACHE_TTL)
def fetch_prices(tickers: tuple, start, end) -> pd.DataFrame:
    """
    Download adjusted closing prices for a sorted tuple of tickers.
    Using tuple (not list) ensures consistent cache keys.
    Prefers Adj Close (dividends + splits adjusted); falls back to Close.
    """
    df = yf.download(list(tickers), start=start, end=end, progress=False, auto_adjust=False)

    if isinstance(df.columns, pd.MultiIndex):
        key = "Adj Close" if "Adj Close" in df.columns.get_level_values(0) else "Close"
        return df.xs(key, level=0, axis=1)

    # Single-ticker download returns a flat DataFrame
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    return pd.DataFrame({tickers[0]: df[col]})
