import streamlit as st
import yfinance as yf
import pandas as pd
from config import CACHE_TTL


@st.cache_data(ttl=CACHE_TTL)
def fetch_stock_info(ticker: str) -> dict:
    """
    Fetch the full yfinance info dict for a single ticker.
    Returns empty dict (not None) on failure so callers can safely use .get().
    """
    try:
        info = yf.Ticker(ticker).info
        # A valid ticker always has a shortName or longName
        if not info.get("shortName") and not info.get("longName"):
            return {}
        return info
    except Exception:
        return {}


@st.cache_data(ttl=CACHE_TTL)
def fetch_stock_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Fetch OHLCV history. Returns empty DataFrame on failure."""
    try:
        return yf.Ticker(ticker).history(period=period)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def fetch_stock_financials(ticker: str) -> dict:
    """
    Fetch annual financial statements (income, balance sheet, cash flow)
    and quarterly earnings dates.
    Each key is an empty DataFrame if unavailable — callers should check .empty.
    """
    out = {
        "financials":    pd.DataFrame(),
        "balance_sheet": pd.DataFrame(),
        "cashflow":      pd.DataFrame(),
        "earnings":      pd.DataFrame(),
    }
    try:
        stock = yf.Ticker(ticker)
        out["financials"]    = stock.financials
        out["balance_sheet"] = stock.balance_sheet
        out["cashflow"]      = stock.cashflow
        try:
            out["earnings"] = stock.earnings_dates
        except Exception:
            pass
    except Exception:
        pass
    return out
