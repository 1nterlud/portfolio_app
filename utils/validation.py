import streamlit as st
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import CACHE_TTL


@st.cache_data(ttl=CACHE_TTL)
def validate_tickers(tickers: tuple) -> dict:
    """
    Validate tickers in parallel using ThreadPoolExecutor.
    Returns {ticker: True/False}.
    Using a tuple parameter for consistent cache keys.
    """
    def _check(t: str) -> tuple[str, bool]:
        try:
            hist = yf.Ticker(t).history(period="5d")
            return t, not hist.empty
        except Exception:
            return t, False

    results = {}
    with ThreadPoolExecutor(max_workers=min(len(tickers), 10)) as executor:
        futures = {executor.submit(_check, t): t for t in tickers}
        for future in as_completed(futures):
            ticker, valid = future.result()
            results[ticker] = valid

    return results
