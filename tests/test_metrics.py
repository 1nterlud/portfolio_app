import numpy as np
import pandas as pd
import pytest

from analytics.metrics import calc_metrics


@pytest.fixture
def synthetic_returns():
    """5 years of 252 trading days, +0.04% daily mean, 1% daily vol — seeded."""
    rng = np.random.default_rng(42)
    n   = 252 * 5
    rets = rng.normal(0.0004, 0.01, n)
    idx  = pd.date_range("2018-01-01", periods=n, freq="B")
    return pd.Series(rets, index=idx)


def test_metric_keys(synthetic_returns):
    m = calc_metrics(synthetic_returns, risk_free=0.04)
    for key in ("cum", "cagr", "vol", "sharpe", "sortino",
                "calmar", "max_dd", "drawdowns", "var_95", "cvar_95", "total_ret"):
        assert key in m


def test_volatility_in_reasonable_range(synthetic_returns):
    m = calc_metrics(synthetic_returns, risk_free=0.04)
    # 1% daily * sqrt(252) ≈ 0.158
    assert 0.13 < m["vol"] < 0.18


def test_max_drawdown_negative(synthetic_returns):
    m = calc_metrics(synthetic_returns, risk_free=0.04)
    assert m["max_dd"] <= 0


def test_var_more_negative_than_cvar(synthetic_returns):
    """CVaR should be more negative (worse) than VaR by construction."""
    m = calc_metrics(synthetic_returns, risk_free=0.04)
    assert m["cvar_95"] <= m["var_95"]


def test_sharpe_finite(synthetic_returns):
    m = calc_metrics(synthetic_returns, risk_free=0.04)
    assert np.isfinite(m["sharpe"])
    assert np.isfinite(m["sortino"])
