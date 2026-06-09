"""
Portfolio optimisation — true efficient frontier (convex), random cloud (for viz),
max-Sharpe and min-vol with optional per-position and per-sector constraints.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from config import FRONTIER_N_PORTFOLIOS, FRONTIER_GRID_POINTS


# ── Random-cloud frontier (for the scatter cloud viz) ────────────────────────

def calc_random_cloud(
    rets: pd.DataFrame,
    risk_free: float = 0.04,
    n_portfolios: int = FRONTIER_N_PORTFOLIOS,
    seed: int = 42,
) -> pd.DataFrame:
    """Sample random portfolios for the cloud overlay behind the frontier."""
    rng     = np.random.default_rng(seed)
    n       = rets.shape[1]
    tickers = rets.columns.tolist()

    rows = []
    for _ in range(n_portfolios):
        w   = rng.dirichlet(np.ones(n))
        pr  = rets.dot(w)
        ret = float(pr.mean() * 252)
        vol = float(pr.std() * np.sqrt(252))
        sharpe = (ret - risk_free) / vol if vol > 0 else 0.0
        rows.append({"Return": ret, "Volatility": vol, "Sharpe": sharpe,
                     **dict(zip(tickers, w))})
    return pd.DataFrame(rows)


# Legacy alias kept for backward compatibility
calc_efficient_frontier = calc_random_cloud


# ── True convex efficient frontier ───────────────────────────────────────────

def _build_constraints(n_assets: int, max_weight: float | None) -> list:
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    return cons


def _bounds(n: int, max_weight: float | None, min_weight: float = 0.0) -> list:
    upper = max_weight if max_weight else 1.0
    return [(min_weight, upper)] * n


def true_efficient_frontier(
    rets: pd.DataFrame,
    risk_free:  float = 0.04,
    n_points:   int   = FRONTIER_GRID_POINTS,
    max_weight: float | None = None,
    min_weight: float = 0.0,
) -> pd.DataFrame:
    """
    Trace the true convex efficient frontier: for a grid of target returns,
    find the min-volatility portfolio with optional per-position caps.
    """
    mu  = rets.mean() * 252
    cov = rets.cov() * 252
    n   = len(mu)
    tickers = rets.columns.tolist()

    if n < 2:
        return pd.DataFrame()

    def port_vol(w):
        return float(np.sqrt(w @ cov.values @ w))

    # Range of feasible target returns
    r_min = float(mu.min())
    r_max = float(mu.max())
    targets = np.linspace(r_min, r_max, n_points)

    bounds = _bounds(n, max_weight, min_weight)
    rows = []
    x0 = np.ones(n) / n

    for tr in targets:
        cons = [
            {"type": "eq", "fun": lambda w: w.sum() - 1},
            {"type": "eq", "fun": lambda w, t=tr: (w @ mu.values) - t},
        ]
        res = minimize(port_vol, x0=x0, method="SLSQP", bounds=bounds,
                       constraints=cons, options={"ftol": 1e-9, "maxiter": 500})
        if res.success:
            v = float(port_vol(res.x))
            sharpe = (tr - risk_free) / v if v > 0 else 0.0
            rows.append({"Return": tr, "Volatility": v, "Sharpe": sharpe,
                         **dict(zip(tickers, res.x))})
    return pd.DataFrame(rows)


# ── Constrained max-Sharpe and min-vol ───────────────────────────────────────

def max_sharpe_portfolio(
    rets: pd.DataFrame,
    risk_free:  float = 0.04,
    max_weight: float | None = None,
    min_weight: float = 0.0,
) -> dict:
    """Max-Sharpe with optional bounds. Returns {} on failure."""
    n       = rets.shape[1]
    tickers = rets.columns.tolist()
    mu_d    = rets.mean().values
    cov     = rets.cov().values

    def neg_sharpe(w):
        ret_a = (w @ mu_d) * 252
        vol_a = float(np.sqrt(w @ cov @ w)) * np.sqrt(252)
        return -(ret_a - risk_free) / vol_a if vol_a > 0 else 0.0

    res = minimize(
        neg_sharpe, x0=np.ones(n) / n, method="SLSQP",
        bounds=_bounds(n, max_weight, min_weight),
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


def min_vol_portfolio(
    rets: pd.DataFrame,
    max_weight: float | None = None,
    min_weight: float = 0.0,
) -> dict:
    n       = rets.shape[1]
    tickers = rets.columns.tolist()
    cov     = rets.cov().values

    def port_vol(w):
        return float(np.sqrt(w @ cov @ w) * np.sqrt(252))

    res = minimize(
        port_vol, x0=np.ones(n) / n, method="SLSQP",
        bounds=_bounds(n, max_weight, min_weight),
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
        "volatility": float(res.fun),
    }
