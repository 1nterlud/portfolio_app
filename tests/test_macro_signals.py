"""Tests for analytics/macro_signals.py — pure macro interpretation rules."""
import numpy as np
import pandas as pd
import pytest

from analytics.macro_signals import yoy_change, macro_signals, macro_regime


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
    assert any("Sahm" in s["title"] and s["tone"] == "danger" for s in sig)


def test_empty_input_no_crash():
    assert macro_signals({}) == []
    assert macro_signals({"VIX": pd.Series(dtype=float)}) == []


def test_every_signal_has_step_and_positioning():
    series = {
        "Spread 10a − 2a":       _monthly([1.0, 0.5, -0.4]),
        "CPI (indice)":          _monthly(100 * (1.05 ** (np.arange(25) / 12))),
        "VIX":                   _monthly([18, 22, 35]),
        "Fed Funds Rate":        _monthly([4.0, 4.5, 5.0, 5.25, 5.25, 5.5, 5.5]),
        "Chômage US":            _monthly([3.5, 3.6, 3.7, 4.0, 4.1, 4.2, 4.2]),
        "Croissance PIB réel":   _monthly([2.5, 1.0, -0.5]),
        "Sentiment conso (UMich)": _monthly([80, 70, 60]),
    }
    sigs = macro_signals(series)
    assert len(sigs) >= 6
    for s in sigs:
        assert s["step"] in ("croissance", "inflation", "fed", "stress")
        assert s["positioning"], f"signal sans positionnement : {s['title']}"


# ── macro_regime ──────────────────────────────────────────────────────────────

def _regime_keys_ok(r):
    assert {"regime", "tone", "resume", "raisons",
            "favoriser", "eviter", "surveiller"} <= set(r)
    assert r["raisons"] and r["favoriser"] and r["eviter"] and r["surveiller"]


def test_regime_recession_from_sahm():
    r = macro_regime({"Chômage US": _monthly([3.5, 3.6, 3.8, 4.0, 4.2])})
    assert r["regime"] == "Risque de récession"
    _regime_keys_ok(r)


def test_regime_recession_from_gdp():
    r = macro_regime({"Croissance PIB réel": _monthly([2.0, 0.5, -1.0])})
    assert r["regime"] == "Risque de récession"


def test_regime_stress_from_vix():
    r = macro_regime({"VIX": _monthly([20, 28, 38])})
    assert r["regime"] == "Stress de marché"
    _regime_keys_ok(r)


def test_regime_overheat():
    cpi = _monthly(100 * (1.06 ** (np.arange(25) / 12)))
    ff  = _monthly([4.0, 4.25, 4.5, 4.75, 5.0, 5.25, 5.5])
    r = macro_regime({"CPI (indice)": cpi, "Fed Funds Rate": ff})
    assert r["regime"] == "Surchauffe inflationniste"


def test_regime_late_cycle_from_inverted_curve():
    r = macro_regime({
        "Spread 10a − 2a":     _monthly([0.5, 0.1, -0.3]),
        "Croissance PIB réel": _monthly([2.5, 2.4, 2.3]),
        "VIX":                 _monthly([15, 16, 17]),
    })
    assert r["regime"] == "Fin de cycle"


def test_regime_slowdown():
    r = macro_regime({
        "Croissance PIB réel": _monthly([2.0, 1.2, 0.8]),
        "Spread 10a − 2a":     _monthly([0.8, 0.9, 1.0]),
    })
    assert r["regime"] == "Ralentissement"


def test_regime_expansion():
    r = macro_regime({
        "Croissance PIB réel": _monthly([2.5, 2.6, 2.8]),
        "Spread 10a − 2a":     _monthly([0.8, 1.0, 1.2]),
        "VIX":                 _monthly([16, 15, 14]),
        "Chômage US":          _monthly([4.0, 3.9, 3.9]),
    })
    assert r["regime"] == "Expansion"
    _regime_keys_ok(r)


def test_regime_severity_order():
    # Sahm + inverted curve + high VIX → recession wins (most severe rule first)
    r = macro_regime({
        "Chômage US":      _monthly([3.5, 3.8, 4.2]),
        "Spread 10a − 2a": _monthly([0.1, -0.2, -0.5]),
        "VIX":             _monthly([25, 32, 40]),
    })
    assert r["regime"] == "Risque de récession"


def test_regime_empty_input_is_expansion_default():
    r = macro_regime({})
    assert r["regime"] == "Expansion"
    assert r["raisons"]  # explains the lack of alert signals
