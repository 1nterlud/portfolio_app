import pandas as pd
from scipy import stats


def calc_mpt(port_rets: pd.Series, bench_rets: pd.Series) -> dict:
    """
    Compute Modern Portfolio Theory statistics vs a benchmark using OLS regression:
        port_ret = alpha + beta * bench_ret + epsilon

    Alpha is de-annualised from the daily intercept (×252).
    R (correlation coefficient) measures linear co-movement with the benchmark.
    """
    aligned = pd.DataFrame({"P": port_rets, "B": bench_rets}).dropna()
    beta, alpha_daily, r_val, p_val, _ = stats.linregress(aligned["B"], aligned["P"])

    return {
        "beta":      beta,
        "alpha_ann": alpha_daily * 252,
        "r_val":     r_val,
        "p_val":     p_val,
    }
