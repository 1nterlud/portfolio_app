"""
Portfolio optimisation — efficient frontier and optimal allocations.
Uses scipy.optimize for max-Sharpe and min-vol, random sampling for the frontier cloud.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from config import FRONTIER_N_PORTFOLIOS


def calc_efficient_frontier(
    rets: pd.DataFrame,
    risk_free: float = 0.04,
    n_portfolios: int = FRONTIER_N_PORTFOLIOS,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Approximate the efficient frontier by sampling random portfolios.
    Returns a DataFrame with columns: Return, Volatility, Sharpe, + one column per ticker.
    """
    rng     = np.random.default_rng(seed)
    n       = rets.shape[1]
    tickers = rets.columns.tolist()

    rows = []
    for _ in range(n_portfolios):
        w = rng.dirichlet(np.ones(n))
        pr  = rets.dot(w)
        ret = float(pr.mean() * 252)
        vol = float(pr.std() * np.sqrt(252))
        sharpe = (ret - risk_free) / vol if vol > 0 else 0.0
        rows.append({"Return": ret, "Volatility": vol, "Sharpe": sharpe,
                     **dict(zip(tickers, w))})
    return pd.DataFrame(rows)


def max_sharpe_portfolio(rets: pd.DataFrame, risk_free: float = 0.04) -> dict:
    """
    Find the maximum-Sharpe portfolio via constrained optimisation (SLSQP).
    Returns {"weights": dict, "return": float, "volatility": float, "sharpe": float}
    or an empty dict if optimisation fails.
    """
    n       = rets.shape[1]
    tickers = rets.columns.tolist()

    def neg_sharpe(w):
        pr  = rets.dot(w)
        ret = pr.mean() * 252
        vol = pr.std() * np.sqrt(252)
        return -(ret - risk_free) / vol if vol > 0 else 0.0

    res = minimize(
        neg_sharpe,
        x0=np.ones(n) / n,
        method="SLSQP",
        bounds=[(0, 1)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"ftol": 1e-9, "maxiter": 1000},
    )
    if not res.success:
        return {}

    w  = res.x
    pr = rets.dot(w)
    return {
        "weights":    dict(zip(tickers, w)),
        "return":     float(pr.mean() * 252),
        "volatility": float(pr.std() * np.sqrt(252)),
        "sharpe":     float(-res.fun),
    }


def min_vol_portfolio(rets: pd.DataFrame) -> dict:
    """
    Find the minimum-volatility portfolio.
    Returns {"weights": dict, "return": float, "volatility": float} or {}.
    """
    n       = rets.shape[1]
    tickers = rets.columns.tolist()

    def portfolio_vol(w):
        return float(rets.dot(w).std() * np.sqrt(252))

    res = minimize(
        portfolio_vol,
        x0=np.ones(n) / n,
        method="SLSQP",
        bounds=[(0, 1)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"ftol": 1e-9, "maxiter": 1000},
    )
    if not res.success:
        return {}

    w  = res.x
    pr = rets.dot(w)
    return {
        "weights":    dict(zip(tickers, w)),
        "return":     float(pr.mean() * 252),
        "volatility": res.fun,
    }
