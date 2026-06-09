import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from config import INFO_CACHE_TTL
from data.normalize import (
    normalize_debt_to_equity, normalize_dividend_yield,
    normalize_sector, normalize_price,
)
from utils.logging_setup import get_logger

log = get_logger("fundamentals")


@st.cache_data(ttl=INFO_CACHE_TTL)
def fetch_fundamentals(tickers: tuple) -> pd.DataFrame:
    """
    One row per ticker with all valuation + quality fields.
    All normalizations go through data.normalize — no duplication.
    Per-ticker errors are caught so a single bad ticker doesn't kill the batch.
    """
    rows = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            rows.append({
                "Symbol":      t,
                "Nom":         info.get("shortName", t),
                "Prix":        normalize_price(info),
                "Secteur":     normalize_sector(info.get("sector")),
                "P/E":         info.get("trailingPE"),
                "Fwd P/E":     info.get("forwardPE"),
                "P/B":         info.get("priceToBook"),
                "PEG":         info.get("pegRatio") or info.get("trailingPegRatio"),
                "EV/EBITDA":   info.get("enterpriseToEbitda"),
                "Beta":        info.get("beta"),
                "ROE":         info.get("returnOnEquity"),
                "Marge nette": info.get("profitMargins"),
                "Div. Yield":  normalize_dividend_yield(info),
                "D/E":         normalize_debt_to_equity(info.get("debtToEquity")),
            })
        except Exception as e:
            log.warning(f"fundamentals({t}) failed: {e}")
            rows.append({"Symbol": t, "Secteur": "Err"})

    df = pd.DataFrame(rows)
    df.attrs["fetched_at"] = datetime.now()
    return df
