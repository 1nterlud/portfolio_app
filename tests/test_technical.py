"""Tests for analytics/technical.py — local RSI, MACD, Bollinger."""
import numpy as np
import pandas as pd
import pytest

from analytics.technical import calc_rsi, calc_macd, calc_bollinger, technical_signals


@pytest.fixture
def trending_up():
    """Strictly rising series — RSI should be very high."""
    return pd.Series(np.linspace(100, 200, 120))


@pytest.fixture
def random_walk():
    rng = np.random.default_rng(7)
    return pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 300)))


# ── RSI ───────────────────────────────────────────────────────────────────────

def test_rsi_bounds(random_walk):
    rsi = calc_rsi(random_walk).dropna()
    assert not rsi.empty
    assert rsi.between(0, 100).all()


def test_rsi_uptrend_high(trending_up):
    rsi = calc_rsi(trending_up).dropna()
    assert rsi.iloc[-1] > 70  # pure uptrend → overbought


def test_rsi_too_short_returns_empty():
    assert calc_rsi(pd.Series([1.0, 2.0, 3.0])).empty


def test_rsi_empty_input():
    assert calc_rsi(pd.Series(dtype=float)).empty


# ── MACD ──────────────────────────────────────────────────────────────────────

def test_macd_columns(random_walk):
    df = calc_macd(random_walk)
    assert list(df.columns) == ["MACD", "MACD_Signal", "MACD_Hist"]
    assert len(df) == len(random_walk)


def test_macd_hist_is_diff(random_walk):
    df = calc_macd(random_walk).dropna()
    np.testing.assert_allclose(df["MACD_Hist"], df["MACD"] - df["MACD_Signal"],
                               atol=1e-10)


def test_macd_constant_series_is_zero():
    df = calc_macd(pd.Series([50.0] * 100))
    assert np.allclose(df["MACD"], 0)
    assert np.allclose(df["MACD_Hist"], 0)


def test_macd_too_short_returns_empty():
    assert calc_macd(pd.Series(np.arange(10, dtype=float))).empty


# ── Bollinger ─────────────────────────────────────────────────────────────────

def test_bollinger_band_ordering(random_walk):
    bb = calc_bollinger(random_walk).dropna()
    assert (bb["BB_Upper"] >= bb["BB_Middle"]).all()
    assert (bb["BB_Middle"] >= bb["BB_Lower"]).all()


def test_bollinger_middle_is_sma(random_walk):
    bb  = calc_bollinger(random_walk, period=20)
    sma = random_walk.rolling(20).mean()
    pd.testing.assert_series_equal(bb["BB_Middle"], sma, check_names=False)


def test_bollinger_too_short_returns_empty():
    assert calc_bollinger(pd.Series(np.arange(5, dtype=float))).empty


# ── Signals snapshot ──────────────────────────────────────────────────────────

def test_signals_keys(random_walk):
    sig = technical_signals(random_walk)
    assert {"rsi", "rsi_state", "macd", "macd_state", "bb_state"} <= set(sig)
    assert 0 <= sig["rsi"] <= 100
    assert sig["macd_state"] in ("Haussier", "Baissier")


def test_signals_insufficient_data():
    assert technical_signals(pd.Series([1.0, 2.0])) == {}
