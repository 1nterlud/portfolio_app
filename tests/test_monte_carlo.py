import numpy as np
import pandas as pd
import pytest

from analytics.monte_carlo import monte_carlo


@pytest.fixture
def synthetic_returns():
    rng = np.random.default_rng(0)
    return pd.Series(rng.normal(0.0005, 0.012, 1000),
                     index=pd.date_range("2020-01-01", periods=1000, freq="B"))


def test_normal_band_ordering(synthetic_returns):
    df = monte_carlo(synthetic_returns, total_val=10_000, distribution="normal")
    last = df.iloc[-1]
    assert last["P5"] < last["P25"] < last["Médiane"] < last["P75"] < last["P95"]


def test_t_distribution_wider_tails(synthetic_returns):
    """Student-t with low df → wider spread between P5 and P95."""
    n_df = monte_carlo(synthetic_returns, total_val=10_000, distribution="normal")
    t_df = monte_carlo(synthetic_returns, total_val=10_000, distribution="t", t_df=5)
    n_spread = n_df.iloc[-1]["P95"] - n_df.iloc[-1]["P5"]
    t_spread = t_df.iloc[-1]["P95"] - t_df.iloc[-1]["P5"]
    # Fat-tail should produce >= the normal spread (allow some sampling noise)
    assert t_spread >= n_spread * 0.85


def test_reproducible_seed(synthetic_returns):
    a = monte_carlo(synthetic_returns, total_val=10_000, seed=123)
    b = monte_carlo(synthetic_returns, total_val=10_000, seed=123)
    pd.testing.assert_frame_equal(a, b)
