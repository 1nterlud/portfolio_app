import numpy as np
import pandas as pd
from config import MC_SEED, MC_N_SIMS, MC_HORIZON_DAYS


def monte_carlo(
    port_rets: pd.Series,
    total_val: float,
    n_sims: int = MC_N_SIMS,
    horizon: int = MC_HORIZON_DAYS,
    seed: int = MC_SEED,
) -> pd.DataFrame:
    """
    Log-normal Monte Carlo simulation.

    Uses log returns (ln(1+r)) for correct geometric compounding — arithmetic
    returns fed into exp(cumsum) would overestimate expected terminal value.
    A fixed seed makes results reproducible across re-runs.
    Returns percentile bands (P5, P25, Median, P75, P95) in dollar terms.
    """
    rng = np.random.default_rng(seed)

    log_rets  = np.log1p(port_rets)
    shocks    = rng.normal(log_rets.mean(), log_rets.std(), (horizon, n_sims))
    paths     = np.exp(np.cumsum(shocks, axis=0)) * total_val

    df = pd.DataFrame(paths)
    return pd.DataFrame({
        "P5":      df.quantile(0.05, axis=1),
        "P25":     df.quantile(0.25, axis=1),
        "Médiane": df.quantile(0.50, axis=1),
        "P75":     df.quantile(0.75, axis=1),
        "P95":     df.quantile(0.95, axis=1),
    })
