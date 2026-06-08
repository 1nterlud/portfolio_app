import pandas as pd
import numpy as np
from config import SP500_SECTORS, MAX_POSITION_WEIGHT, MAX_SECTOR_WEIGHT, ALLOCATION_MIN_SECTOR_PCT


def build_sector_comparison(merged: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate portfolio sector weights and join with S&P 500 reference.
    ETFs and tickers without sector data (N/A, Err) are excluded — their
    weight is logged separately so callers can surface it to the user.
    """
    sector_data = (
        merged[~merged["Secteur"].isin(["N/A", "Err", None, ""])]
        .groupby("Secteur")["W"]
        .sum()
        .reset_index()
        .rename(columns={"W": "Portefeuille"})
    )
    sp_df  = pd.DataFrame(SP500_SECTORS.items(), columns=["Secteur", "S&P 500"])
    result = pd.merge(sector_data, sp_df, on="Secteur", how="outer").fillna(0)

    # Expose the ETF/unclassified weight so the UI can mention it
    unclassified_w = merged[merged["Secteur"].isin(["N/A", "Err", None, ""])]["W"].sum()
    result.attrs["unclassified_weight"] = float(unclassified_w)
    return result


def calc_diversification_score(
    weights: pd.Series,
    sector_weights: pd.Series,
) -> dict:
    """
    Score 0–100 combining:
      - 60 % : HHI-based position concentration (normalised)
      - 40 % : sector coverage vs S&P 500

    ETF positions (excluded from sector_weights) are NOT penalised —
    an ETF holder may be well-diversified even if their sector map is thin.
    """
    n   = len(weights)
    hhi = float((weights ** 2).sum())
    hhi_score = max(0.0, (1 - hhi) / (1 - 1 / n) * 100) if n > 1 else 0.0

    # Only count sectors with a meaningful allocation
    n_sectors = int((sector_weights >= ALLOCATION_MIN_SECTOR_PCT).sum())

    # If most weight is unclassified (ETFs), give a partial sector bonus
    # so a "SPY + 2 stocks" portfolio isn't unfairly penalised.
    sec_score = min(100.0, n_sectors / len(SP500_SECTORS) * 100)

    score = round(0.6 * hhi_score + 0.4 * sec_score)

    if score >= 70:    label, color = "Bien diversifié",         "green"
    elif score >= 45:  label, color = "Diversification modérée", "orange"
    else:              label, color = "Peu diversifié",           "red"

    return {"score": score, "label": label, "color": color, "hhi": hhi}


def concentration_alerts(df_port: pd.DataFrame, comp_df: pd.DataFrame) -> list:
    """Return warning strings for positions or sectors over threshold."""
    alerts = []
    for _, row in df_port.iterrows():
        if row["W"] > MAX_POSITION_WEIGHT:
            alerts.append(
                f"**{row['Symbol']}** représente {row['W']:.1%} du portefeuille "
                f"(seuil : {MAX_POSITION_WEIGHT:.0%})"
            )
    for _, row in comp_df.iterrows():
        if row.get("Portefeuille", 0) > MAX_SECTOR_WEIGHT:
            alerts.append(
                f"Secteur **{row['Secteur']}** : {row['Portefeuille']:.1%} "
                f"(seuil : {MAX_SECTOR_WEIGHT:.0%})"
            )
    return alerts


def top_contributors(
    df_port: pd.DataFrame,
    rets: pd.DataFrame,
    horizon: int = 21,
) -> pd.DataFrame:
    """Approximate contribution: weight × cumulative return over the last `horizon` days."""
    recent = rets.iloc[-horizon:]
    rows = []
    for _, row in df_port.iterrows():
        sym = row["Symbol"]
        if sym in recent.columns:
            cum_ret = (1 + recent[sym]).prod() - 1
            rows.append({"Symbol": sym, "Contribution": row["W"] * cum_ret, "Retour": cum_ret})
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("Contribution", ascending=False).reset_index(drop=True)
