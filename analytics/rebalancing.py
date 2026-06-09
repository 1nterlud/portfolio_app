"""
Generate concrete rebalancing instructions: target weights → buy/sell each ticker.
"""
import pandas as pd


def build_rebalancing_plan(
    df_port:      pd.DataFrame,
    target_w:     dict,
    last_prices:  pd.Series,
    total_val:    float,
    min_trade_pct: float = 0.005,   # ignore trades < 0.5% of portfolio
) -> pd.DataFrame:
    """
    Produce a per-ticker action plan to reach target weights.

    df_port must have: Symbol, Qty, W
    target_w: {ticker: weight ∈ [0,1]}
    last_prices: indexed by ticker
    Returns DataFrame: Symbol, Qty actuelle, Qty cible, Δ Qty, Action, Montant $
    """
    rows = []
    all_syms = set(df_port["Symbol"]) | set(target_w.keys())

    for sym in all_syms:
        price = last_prices.get(sym)
        if price is None or price <= 0:
            continue

        cur_qty = float(df_port.loc[df_port["Symbol"] == sym, "Qty"].sum())
        tgt_w   = float(target_w.get(sym, 0))
        tgt_val = tgt_w * total_val
        tgt_qty = tgt_val / price

        delta_qty = tgt_qty - cur_qty
        delta_val = delta_qty * price

        # Skip negligible moves
        if abs(delta_val) / total_val < min_trade_pct:
            continue

        action = "ACHETER" if delta_qty > 0 else "VENDRE"
        rows.append({
            "Symbol":      sym,
            "Qty actuelle": round(cur_qty, 2),
            "Qty cible":    round(tgt_qty, 2),
            "Δ Qty":        round(delta_qty, 2),
            "Action":       action,
            "Montant $":    round(abs(delta_val), 0),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("Montant $", ascending=False).reset_index(drop=True)
