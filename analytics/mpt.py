import numpy as np
import pandas as pd
from scipy import stats


def calc_mpt(port_rets: pd.Series, bench_rets: pd.Series) -> dict:
    """
    MPT statistics vs a benchmark via OLS:
        port_ret = alpha + beta * bench_ret + epsilon

    Returns alpha (annualized), beta, correlation, p-value, tracking error,
    information ratio, and capture ratios.
    """
    aligned = pd.DataFrame({"P": port_rets, "B": bench_rets}).dropna()
    if len(aligned) < 30:
        return {}

    beta, alpha_daily, r_val, p_val, _ = stats.linregress(aligned["B"], aligned["P"])

    # Active return = portfolio - benchmark (the alpha series)
    active = aligned["P"] - aligned["B"]
    tracking_error = float(active.std() * np.sqrt(252))
    info_ratio     = float(active.mean() * 252 / tracking_error) if tracking_error > 0 else 0.0

    # Up- / down-capture
    up_mask   = aligned["B"] > 0
    down_mask = aligned["B"] < 0
    up_cap    = (aligned.loc[up_mask, "P"].mean() / aligned.loc[up_mask, "B"].mean()
                 if up_mask.any() and aligned.loc[up_mask, "B"].mean() != 0 else None)
    down_cap  = (aligned.loc[down_mask, "P"].mean() / aligned.loc[down_mask, "B"].mean()
                 if down_mask.any() and aligned.loc[down_mask, "B"].mean() != 0 else None)

    return {
        "beta":           float(beta),
        "alpha_ann":      float(alpha_daily * 252),
        "r_val":          float(r_val),
        "p_val":          float(p_val),
        "tracking_error": tracking_error,
        "info_ratio":     info_ratio,
        "up_capture":     float(up_cap)   if up_cap   is not None else None,
        "down_capture":   float(down_cap) if down_cap is not None else None,
    }
