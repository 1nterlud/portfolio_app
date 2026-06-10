"""Tests for analytics/macro_signals.py — pure macro interpretation rules."""
import numpy as np
import pandas as pd
import pytest

from analytics.macro_signals import yoy_change, macro_signals


def _monthly(values, end="2026-06-01"):
    idx = pd.date_range(end=end, periods=len(values), freq="MS")
    return pd.Series(values, index=idx, dtype=float)


# ── yoy_change ────────────────────────────────────────────────────────────────

def test_yoy_change_known_value():
    # Index going 100 → 105 over 12 months = +5% YoY
    s = _monthly(np.linspace(100, 105, 13))
    yoy = yoy_change(s).dropna()
    assert yoy.iloc[-1] == pytest.approx(5.0, abs=0.01)


def test_yoy_change_too_short():
    assert yoy_change(_monthly([1, 2, 3])).empty


def test_yoy_change_empty():
    assert yoy_change(pd.Series(dtype=float)).empty


# ── macro_signals rules ───────────────────────────────────────────────────────

def test_inverted_curve_is_danger():
    sig = macro_signals({"Spread 10a − 2a": _monthly([1.0, 0.5, -0.4])})
    assert any(s["tone"] == "danger" and "inversée" in s["title"] for s in sig)


def test_normal_curve_is_success():
    sig = macro_signals({"Spread 10a − 2a": _monthly([1.0, 1.2, 1.5])})
    assert any(s["tone"] == "success" for s in sig)


def test_high_inflation_flagged():
    # CPI index rising 6% YoY
    cpi = _monthly(100 * (1.06 ** (np.arange(25) / 12)))
    sig = macro_signals({"CPI (indice)": cpi})
    assert any("Inflation élevée" in s["title"] for s in sig)


def test_low_inflation_is_success():
    cpi = _monthly(100 * (1.018 ** (np.arange(25) / 12)))
    sig = macro_signals({"CPI (indice)": cpi})
    assert any("maîtrisée" in s["title"] for s in sig)


def test_vix_regimes():
    high = macro_signals({"VIX": _monthly([18, 22, 35])})
    calm = macro_signals({"VIX": _monthly([22, 18, 14])})
    assert any(s["tone"] == "danger" for s in high)
    assert any(s["tone"] == "success" for s in calm)


def test_fed_easing_detected():
    # 5.25% six months ago → 4.50% now
    ff = _monthly([5.25, 5.25, 5.0, 4.75, 4.75, 4.5, 4.5])
    sig = macro_signals({"Fed Funds Rate": ff})
    assert any("assouplissement" in s["title"].lower() for s in sig)


def test_sahm_rule_triggers():
    # Unemployment 3.5% low → 4.2% now (+0.7 pt)
    un = _monthly([3.5, 3.5, 3.6, 3.7, 3.9, 4.0, 4.2])
    sig = macro_signals({"Chômage US": un})
    assert any("Sahm" in s["message"] for s in sig)


def test_empty_input_no_crash():
    assert macro_signals({}) == []
    assert macro_signals({"VIX": pd.Series(dtype=float)}) == []
