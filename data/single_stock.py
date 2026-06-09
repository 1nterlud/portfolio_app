import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from config import INFO_CACHE_TTL, PRICE_CACHE_TTL
from utils.logging_setup import get_logger

log = get_logger("single_stock")


@st.cache_data(ttl=INFO_CACHE_TTL)
def fetch_stock_info(ticker: str) -> dict:
    """Full yfinance info dict; {} on failure (so callers can .get())."""
    try:
        info = yf.Ticker(ticker.upper()).info
        # yfinance 0.2.x may omit name fields but still returns valid data;
        # treat as found if ANY meaningful market field is present
        _present = ("symbol", "shortName", "longName",
                    "regularMarketPrice", "currentPrice", "quoteType")
        if not info or not any(info.get(f) for f in _present):
            log.warning(f"ticker {ticker} returned no recognisable fields")
            return {}
        return info
    except Exception as e:
        log.error(f"fetch_stock_info({ticker}) failed: {e}")
        return {}


@st.cache_data(ttl=PRICE_CACHE_TTL)
def fetch_stock_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        return yf.Ticker(ticker.upper()).history(period=period)
    except Exception as e:
        log.error(f"history({ticker}, {period}) failed: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=INFO_CACHE_TTL)
def fetch_stock_financials(ticker: str) -> dict:
    out = {
        "financials":    pd.DataFrame(),
        "balance_sheet": pd.DataFrame(),
        "cashflow":      pd.DataFrame(),
        "earnings":      pd.DataFrame(),
    }
    try:
        stock = yf.Ticker(ticker.upper())
        out["financials"]    = stock.financials
        out["balance_sheet"] = stock.balance_sheet
        out["cashflow"]      = stock.cashflow
        try:
            out["earnings"] = stock.earnings_dates
        except Exception:
            pass
    except Exception as e:
        log.error(f"financials({ticker}) failed: {e}")
    return out


@st.cache_data(ttl=INFO_CACHE_TTL)
def fetch_stock_news(ticker: str, limit: int = 5) -> list[dict]:
    """Top N news headlines for a ticker. Each item: title, publisher, link, published."""
    try:
        raw = yf.Ticker(ticker.upper()).news or []
        items = []
        for n in raw[:limit]:
            content = n.get("content") or n
            title   = content.get("title") or n.get("title")
            pub     = content.get("provider", {}).get("displayName") if isinstance(content.get("provider"), dict) else n.get("publisher")
            link    = (
                content.get("canonicalUrl", {}).get("url")
                if isinstance(content.get("canonicalUrl"), dict) else n.get("link")
            )
            ts      = content.get("pubDate") or n.get("providerPublishTime")
            if isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            elif isinstance(ts, str):
                ts = ts[:10]
            if title:
                items.append({"title": title, "publisher": pub or "—",
                              "link": link or "", "date": ts or ""})
        return items
    except Exception as e:
        log.warning(f"news({ticker}) failed: {e}")
        return []


@st.cache_data(ttl=INFO_CACHE_TTL)
def fetch_insider_transactions(ticker: str) -> pd.DataFrame:
    """Recent insider transactions (last ~6 months from yfinance)."""
    try:
        df = yf.Ticker(ticker.upper()).insider_transactions
        if df is None or df.empty:
            return pd.DataFrame()
        return df.head(10)
    except Exception as e:
        log.warning(f"insiders({ticker}) failed: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=INFO_CACHE_TTL)
def fetch_institutional_holders(ticker: str) -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker.upper()).institutional_holders
        if df is None or df.empty:
            return pd.DataFrame()
        return df.head(10)
    except Exception as e:
        log.warning(f"inst_holders({ticker}) failed: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=INFO_CACHE_TTL)
def fetch_earnings_calendar(ticker: str) -> dict | None:
    """Next earnings date + EPS estimate."""
    try:
        cal = yf.Ticker(ticker.upper()).calendar
        if cal is None:
            return None
        if isinstance(cal, dict):
            return cal
        # DataFrame form
        if hasattr(cal, "to_dict"):
            d = cal.to_dict()
            return d
    except Exception as e:
        log.warning(f"calendar({ticker}) failed: {e}")
    return None
