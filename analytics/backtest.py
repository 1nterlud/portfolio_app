"""
Backtest a target allocation against the actual portfolio over the historical window.
Useful for: "What if I'd held the max-Sharpe allocation for the past N years?"
"""
import pandas as pd
import numpy as np


def backtest_allocation(
    rets:    pd.DataFrame,
    weights: dict,
    rebalance_freq_days: int = 63,   # quarterly by default
) -> pd.Series:
    """
    Simulate the cumulative value of a static-target allocation, rebalanced periodically.

    Each sleeve grows with its asset return until the rebalance day, when total
    value is redistributed back to the target weights.
    Returns the cumulative value series starting at 1.0.
    """
    tickers = [t for t in weights if t in rets.columns]
    if not tickers:
        return pd.Series(dtype=float)

    w_vec = np.array([weights[t] for t in tickers], dtype=float)
    s     = w_vec.sum()
    if s <= 0:
        return pd.Series(dtype=float)
    w_vec = w_vec / s

    sub = rets[tickers].copy()
    n   = len(sub)
    val = np.ones(n)
    cur_alloc = w_vec.copy()  # dollar allocation to each sleeve, total = 1.0 at t0

    for i in range(1, n):
        cur_alloc = cur_alloc * (1 + sub.iloc[i].values)
        total = cur_alloc.sum()
        val[i] = total
        if i % rebalance_freq_days == 0 and total > 0:
            cur_alloc = total * w_vec

    return pd.Series(val, index=sub.index, name="Backtest")


def compare_backtests(
    rets:        pd.DataFrame,
    current_w:   dict,
    target_w:    dict,
    benchmark_rets: pd.Series | None = None,
    benchmark_name: str = "Benchmark",
) -> pd.DataFrame:
    """Build a DataFrame with cumulative paths: Actuel / Cible / Benchmark."""
    cur = backtest_allocation(rets, current_w)
    opt = backtest_allocation(rets, target_w)

    df = pd.DataFrame({"Actuel": cur, "Cible": opt})
    if benchmark_rets is not None:
        bench = (1 + benchmark_rets.reindex(df.index).fillna(0)).cumprod()
        df[benchmark_name] = bench
    return df.dropna(how="all")


def backtest_summary(cum: pd.Series) -> dict:
    """One-shot CAGR/Vol/Sharpe/Drawdown for a backtest series."""
    if cum.empty or len(cum) < 2:
        return {}
    years = max((cum.index[-1] - cum.index[0]).days / 365.25, 0.1)
    cagr  = cum.iloc[-1] ** (1 / years) - 1
    daily = cum.pct_change().dropna()
    vol   = float(daily.std() * np.sqrt(252))
    sharpe = float(daily.mean() * 252 / vol) if vol > 0 else 0.0
    max_dd = float((cum / cum.cummax() - 1).min())
    return {"cagr": cagr, "vol": vol, "sharpe": sharpe, "max_dd": max_dd,
            "total_ret": float(cum.iloc[-1] - 1)}
