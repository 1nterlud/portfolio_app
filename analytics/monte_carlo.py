import numpy as np
import pandas as pd
from scipy import stats
from config import MC_SEED, MC_N_SIMS, MC_HORIZON_DAYS


def monte_carlo(
    port_rets: pd.Series,
    total_val: float,
    n_sims:    int   = MC_N_SIMS,
    horizon:   int   = MC_HORIZON_DAYS,
    seed:      int   = MC_SEED,
    distribution: str = "normal",   # "normal" or "t" (fat tails)
    t_df:      int   = 5,           # degrees of freedom for Student-t
) -> pd.DataFrame:
    """
    Log-normal Monte Carlo simulation.

    distribution='normal' → standard Geometric Brownian Motion shocks.
    distribution='t'      → Student-t shocks scaled to match historical volatility,
                            for fatter tails (more realistic crash modelling).

    Returns percentile bands (P5, P25, Median, P75, P95) in dollar terms.
    """
    rng = np.random.default_rng(seed)

    log_rets = np.log1p(port_rets)
    mu  = log_rets.mean()
    sig = log_rets.std()

    if distribution == "t":
        # Sample from Student-t, rescale so std matches historical
        raw    = rng.standard_t(df=t_df, size=(horizon, n_sims))
        # variance of t with df is df/(df-2) ; rescale to 1, then to sig
        scale  = sig / np.sqrt(t_df / (t_df - 2)) if t_df > 2 else sig
        shocks = mu + raw * scale
    else:
        shocks = rng.normal(mu, sig, (horizon, n_sims))

    paths = np.exp(np.cumsum(shocks, axis=0)) * total_val

    df = pd.DataFrame(paths)
    return pd.DataFrame({
        "P5":      df.quantile(0.05, axis=1),
        "P25":     df.quantile(0.25, axis=1),
        "Médiane": df.quantile(0.50, axis=1),
        "P75":     df.quantile(0.75, axis=1),
        "P95":     df.quantile(0.95, axis=1),
    })
