"""
FRED macro data — rates & yield curve, inflation, real economy, markets.
Requires FRED_API_KEY in .streamlit/secrets.toml or env (free key, optional).
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Catalog: category → {label: (series_id, unit)}
MACRO_CATALOG = {
    "Taux & Courbe": {
        "Fed Funds Rate":      ("FEDFUNDS",     "%"),
        "Treasury 2 ans":      ("DGS2",         "%"),
        "Treasury 10 ans":     ("DGS10",        "%"),
        "Spread 10a − 2a":     ("T10Y2Y",       "pt"),
        "Mortgage 30 ans":     ("MORTGAGE30US", "%"),
    },
    "Inflation": {
        "CPI (indice)":        ("CPIAUCSL",     "idx"),
        "Core CPI (indice)":   ("CPILFESL",     "idx"),
    },
    "Économie réelle": {
        "Chômage US":          ("UNRATE",       "%"),
        "Croissance PIB réel": ("A191RL1Q225SBEA", "%"),
        "Sentiment conso (UMich)": ("UMCSENT",  "idx"),
    },
    "Marchés": {
        "VIX":                 ("VIXCLS",       "pt"),
        "Dollar Index (broad)": ("DTWEXBGS",    "idx"),
    },
}


def _get_key() -> str | None:
    try:
        return st.secrets["FRED_API_KEY"]
    except Exception:
        import os
        return os.environ.get("FRED_API_KEY")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_macro_series(series_id: str, years: int = 10) -> pd.Series:
    """Fetch a single FRED series as a dated pd.Series. Empty on failure."""
    key = _get_key()
    if not key:
        return pd.Series(dtype=float)
    start = (datetime.today() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            _BASE,
            params={
                "series_id":         series_id,
                "api_key":           key,
                "file_type":         "json",
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
def fetch_macro_category(category: str, years: int = 10) -> dict:
    """All series of one catalog category: {label: pd.Series}."""
    out = {}
    for label, (sid, _unit) in MACRO_CATALOG.get(category, {}).items():
        out[label] = fetch_macro_series(sid, years)
    return out


def macro_available() -> bool:
    return bool(_get_key())
