import numpy as np
import pandas as pd
import pytest

from analytics.optimization import (
    max_sharpe_portfolio, min_vol_portfolio, true_efficient_frontier,
)


@pytest.fixture
def synthetic_rets():
    """3-asset returns: low-vol, medium, high-vol — uncorrelated."""
    rng = np.random.default_rng(0)
    n   = 1000
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "BOND":  rng.normal(0.0001, 0.003, n),
        "STOCK": rng.normal(0.0006, 0.012, n),
        "TECH":  rng.normal(0.0012, 0.025, n),
    }, index=idx)


def test_max_sharpe_returns_weights(synthetic_rets):
    res = max_sharpe_portfolio(synthetic_rets, risk_free=0.04)
    assert "weights" in res
    assert abs(sum(res["weights"].values()) - 1.0) < 1e-4


def test_max_weight_constraint(synthetic_rets):
    res = max_sharpe_portfolio(synthetic_rets, risk_free=0.04, max_weight=0.5)
    for w in res["weights"].values():
        assert w <= 0.5 + 1e-3


def test_min_vol_lower_vol_than_max_sharpe(synthetic_rets):
    mv  = min_vol_portfolio(synthetic_rets)
    ms  = max_sharpe_portfolio(synthetic_rets, risk_free=0.04)
    assert mv["volatility"] <= ms["volatility"] + 1e-3


def test_true_frontier_monotonic(synthetic_rets):
    df = true_efficient_frontier(synthetic_rets, risk_free=0.04, n_points=30)
    # Frontier returns should be sorted ascending
    assert not df.empty
    assert df["Return"].is_monotonic_increasing


def test_frontier_constraint_caps_weights(synthetic_rets):
    df = true_efficient_frontier(synthetic_rets, max_weight=0.4)
    tick_cols = [c for c in df.columns if c in synthetic_rets.columns]
    assert (df[tick_cols] <= 0.4 + 1e-3).all().all()
