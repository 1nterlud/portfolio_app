"""
FRED macro data — Fed Funds Rate, CPI, 10Y Treasury, Unemployment.
Requires FRED_API_KEY in .streamlit/secrets.toml or env.
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

_BASE = "https://api.stlouisfed.org/fred/series/observations"

_SERIES = {
    "Fed Funds Rate":    "FEDFUNDS",
    "Inflation (CPI)":  "CPIAUCSL",
    "10Y Treasury":     "DGS10",
    "Chômage US":        "UNRATE",
    "VIX":              "VIXCLS",
}


def _get_key() -> str | None:
    try:
        return st.secrets["FRED_API_KEY"]
    except Exception:
        import os
        return os.environ.get("FRED_API_KEY")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_macro_series(series_id: str, years: int = 3) -> pd.Series:
    """Fetch a single FRED series as a dated pd.Series."""
    key = _get_key()
    if not key:
        return pd.Series(dtype=float)
    start = (datetime.today() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            _BASE,
            params={
                "series_id":       series_id,
                "api_key":         key,
                "file_type":       "json",
                "observation_start": start,
            },
            timeout=10,
        )
        r.raise_for_status()
        obs = r.json().get("observations", [])
        s = pd.Series(
            {o["date"]: float(o["value"]) for o in obs if o["value"] != "."},
            dtype=float,
        )
        s.index = pd.to_datetime(s.index)
        return s.sort_index()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_macro(years: int = 3) -> dict[str, pd.Series]:
    """Return all key macro series keyed by human-readable name."""
    return {name: fetch_macro_series(sid, years) for name, sid in _SERIES.items()}


def macro_available() -> bool:
    return bool(_get_key())
