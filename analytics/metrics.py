import numpy as np
import pandas as pd


def calc_metrics(port_rets: pd.Series, risk_free: float) -> dict:
    """
    Compute all performance and risk metrics for the portfolio.

    All annualisations assume 252 trading days/year.
    Downside deviation uses the daily risk-free rate as the minimum acceptable return (MAR).
    """
    rf_daily = (1 + risk_free) ** (1 / 252) - 1

    # Cumulative return (geometric)
    cum = (1 + port_rets).cumprod()

    # CAGR
    years = max((port_rets.index[-1] - port_rets.index[0]).days / 365.25, 0.1)
    cagr = cum.iloc[-1] ** (1 / years) - 1

    # Annualised mean and volatility
    mu_ann = port_rets.mean() * 252
    vol    = port_rets.std()  * np.sqrt(252)

    # Sharpe — excess return per unit of total risk
    sharpe = (mu_ann - risk_free) / vol if vol else 0.0

    # Sortino — only penalises downside deviation below the daily MAR
    downside = np.minimum(0.0, port_rets - rf_daily)
    dd_dev   = np.sqrt((downside ** 2).mean()) * np.sqrt(252)
    sortino  = (mu_ann - risk_free) / dd_dev if dd_dev else 0.0

    # Drawdowns
    roll_max  = cum.cummax()
    drawdowns = cum / roll_max - 1
    max_dd    = drawdowns.min()

    # Calmar — CAGR relative to the worst peak-to-trough loss
    calmar = cagr / abs(max_dd) if max_dd else 0.0

    # Historical VaR and CVaR (1-day, 95 % confidence)
    var_95  = np.percentile(port_rets, 5)
    cvar_95 = port_rets[port_rets < var_95].mean()

    return {
        "cum":       cum,
        "cagr":      cagr,
        "vol":       vol,
        "mu_ann":    mu_ann,
        "sharpe":    sharpe,
        "sortino":   sortino,
        "calmar":    calmar,
        "max_dd":    max_dd,
        "drawdowns": drawdowns,
        "var_95":    var_95,
        "cvar_95":   cvar_95,
        "total_ret": cum.iloc[-1] - 1,
    }
