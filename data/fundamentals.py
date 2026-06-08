import streamlit as st
import yfinance as yf
import pandas as pd
from config import CACHE_TTL


def _calc_div_yield(info: dict) -> float | None:
    """Compute yield from dividendRate/price — bypasses yfinance's inconsistent dividendYield."""
    rate  = info.get("dividendRate")
    price = info.get("currentPrice") or info.get("regularMarketPreviousClose")
    if rate and price and float(price) > 0:
        return float(rate) / float(price)
    return None

_TECH_KEYWORDS = ("Technology", "Software", "Hardware", "Semiconductor", "Internet")


@st.cache_data(ttl=CACHE_TTL)
def fetch_fundamentals(tickers: tuple) -> pd.DataFrame:
    """
    Fetch fundamental data for each ticker.
    Returns one row per ticker with extended valuation and quality fields.
    Individual ticker errors are caught so one bad ticker doesn't abort the batch.
    """
    rows = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            sec  = info.get("sector") or "N/A"
            if any(kw in sec for kw in _TECH_KEYWORDS):
                sec = "Technology"

            # Normalise D/E — yfinance is inconsistent (ratio vs %)
            de_raw = info.get("debtToEquity")
            de     = (de_raw / 100) if (de_raw is not None and de_raw > 10) else de_raw

            rows.append({
                "Symbol":       t,
                "Nom":          info.get("shortName", t),
                "Prix":         info.get("currentPrice") or info.get("regularMarketPreviousClose"),
                "Secteur":      sec,
                # Valuation
                "P/E":          info.get("trailingPE"),
                "Fwd P/E":      info.get("forwardPE"),
                "P/B":          info.get("priceToBook"),
                "PEG":          info.get("pegRatio"),
                "EV/EBITDA":    info.get("enterpriseToEbitda"),
                # Returns & quality
                "Beta":         info.get("beta"),
                "ROE":          info.get("returnOnEquity"),
                "Marge nette":  info.get("profitMargins"),
                "Div. Yield":   _calc_div_yield(info),
                # Balance sheet
                "D/E":          de,
            })
        except Exception:
            rows.append({"Symbol": t, "Secteur": "Err"})

    return pd.DataFrame(rows)
