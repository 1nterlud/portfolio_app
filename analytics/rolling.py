"""
Rolling metrics — Sharpe and Drawdown over a moving window.
Detects regime changes that point-in-time metrics hide.
"""
import numpy as np
import pandas as pd


def rolling_sharpe(port_rets: pd.Series, risk_free: float = 0.04,
                   window: int = 90) -> pd.Series:
    """N-day rolling Sharpe ratio (annualized)."""
    rf_daily = (1 + risk_free) ** (1 / 252) - 1
    excess   = port_rets - rf_daily
    mean     = excess.rolling(window).mean() * 252
    vol      = port_rets.rolling(window).std() * np.sqrt(252)
    return (mean / vol).dropna()


def rolling_volatility(port_rets: pd.Series, window: int = 60) -> pd.Series:
    """N-day rolling annualized volatility."""
    return (port_rets.rolling(window).std() * np.sqrt(252)).dropna()


def rolling_drawdown(port_rets: pd.Series, window: int = 252) -> pd.Series:
    """Rolling max drawdown over the past N days, recomputed at each point."""
    cum = (1 + port_rets).cumprod()
    out = []
    for i in range(len(cum)):
        start = max(0, i - window + 1)
        sub = cum.iloc[start:i+1]
        dd = (sub.iloc[-1] / sub.max()) - 1
        out.append(dd)
    return pd.Series(out, index=cum.index).dropna()


def rolling_beta(port_rets: pd.Series, bench_rets: pd.Series,
                 window: int = 90) -> pd.Series:
    """Rolling beta vs benchmark using N-day OLS."""
    aligned = pd.DataFrame({"P": port_rets, "B": bench_rets}).dropna()
    cov  = aligned["P"].rolling(window).cov(aligned["B"])
    var  = aligned["B"].rolling(window).var()
    return (cov / var).dropna()
