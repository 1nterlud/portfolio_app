"""
Stress tests — replay historical crisis periods on current portfolio weights.
Uses the actual asset returns during the period; if data is missing, falls back to benchmark proxy.
"""
import pandas as pd
import yfinance as yf
import streamlit as st
from config import STRESS_SCENARIOS, CACHE_TTL
from utils.logging_setup import get_logger

log = get_logger("stress")


@st.cache_data(ttl=CACHE_TTL)
def _fetch_stress_prices(tickers: tuple, start: str, end: str) -> pd.DataFrame:
    try:
        df = yf.download(list(tickers), start=start, end=end,
                         progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            key = "Adj Close" if "Adj Close" in df.columns.get_level_values(0) else "Close"
            return df.xs(key, level=0, axis=1)
        col = "Adj Close" if "Adj Close" in df.columns else "Close"
        return pd.DataFrame({tickers[0]: df[col]})
    except Exception as e:
        log.warning(f"stress fetch failed for {tickers} {start}-{end}: {e}")
        return pd.DataFrame()


def run_stress_test(weights: dict, scenario_name: str, fallback_ticker: str = "SPY") -> dict:
    """
    Apply current weights to historical returns from the scenario window.
    Returns {return, max_dd, n_days, missing_tickers}.
    """
    if scenario_name not in STRESS_SCENARIOS:
        return {}
    start, end = STRESS_SCENARIOS[scenario_name]
    tickers = tuple(sorted(weights.keys()))
    prices  = _fetch_stress_prices(tickers, start, end)

    if prices.empty:
        return {"return": None, "max_dd": None, "available": False}

    rets = prices.pct_change().dropna()
    valid = [t for t in tickers if t in rets.columns]
    missing = [t for t in tickers if t not in valid]

    # For missing tickers, substitute the fallback (SPY) returns
    if missing:
        fb = _fetch_stress_prices((fallback_ticker,), start, end)
        if not fb.empty:
            fb_rets = fb[fallback_ticker].pct_change().dropna()
            for t in missing:
                rets[t] = fb_rets

    # Realign weights to columns we now have
    w = pd.Series(weights).reindex(rets.columns).fillna(0)
    w = w / w.sum() if w.sum() > 0 else w

    port_rets = rets[w.index].dot(w.values)
    cum       = (1 + port_rets).cumprod()
    max_dd    = (cum / cum.cummax() - 1).min()

    return {
        "scenario":  scenario_name,
        "window":    f"{start} → {end}",
        "return":    float(cum.iloc[-1] - 1),
        "max_dd":    float(max_dd),
        "n_days":    int(len(port_rets)),
        "missing":   missing,
        "available": True,
    }


def run_all_stress(weights: dict) -> pd.DataFrame:
    """Run every defined scenario and return a tidy DataFrame."""
    rows = []
    for name in STRESS_SCENARIOS:
        res = run_stress_test(weights, name)
        if res.get("available"):
            rows.append({
                "Scénario":      name,
                "Période":       res["window"],
                "Rendement":     res["return"],
                "Max DD":        res["max_dd"],
                "Tickers absents": ", ".join(res["missing"]) if res["missing"] else "—",
            })
    return pd.DataFrame(rows)
