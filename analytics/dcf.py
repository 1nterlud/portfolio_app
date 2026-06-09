"""
Simple two-stage DCF — for the Stock Research page.
NOT investment advice; meant as an educational what-if tool.
"""


def two_stage_dcf(
    fcf_base:        float,
    growth_high:     float,     # years 1-5
    growth_terminal: float,     # year 6+
    wacc:            float,
    shares_out:      float,
    net_debt:        float = 0,
    horizon_years:   int   = 5,
) -> dict:
    """
    Two-stage DCF: high-growth period then terminal value (Gordon).

    Returns {equity_value, per_share, npv_explicit, npv_terminal, assumptions}.
    """
    if wacc <= growth_terminal:
        return {"error": "WACC doit être supérieur au taux de croissance terminal."}
    if shares_out is None or shares_out <= 0:
        return {"error": "Shares outstanding manquant."}

    # Explicit period
    fcf      = fcf_base
    npv_exp  = 0
    flows    = []
    for year in range(1, horizon_years + 1):
        fcf *= (1 + growth_high)
        pv   = fcf / ((1 + wacc) ** year)
        npv_exp += pv
        flows.append({"year": year, "fcf": fcf, "pv": pv})

    # Terminal value at year horizon_years, discounted back
    tv      = fcf * (1 + growth_terminal) / (wacc - growth_terminal)
    npv_tv  = tv / ((1 + wacc) ** horizon_years)

    enterprise = npv_exp + npv_tv
    equity     = enterprise - (net_debt or 0)
    per_share  = equity / shares_out

    return {
        "equity_value": equity,
        "per_share":    per_share,
        "npv_explicit": npv_exp,
        "npv_terminal": npv_tv,
        "enterprise":   enterprise,
        "flows":        flows,
        "assumptions": {
            "fcf_base":        fcf_base,
            "growth_high":     growth_high,
            "growth_terminal": growth_terminal,
            "wacc":            wacc,
            "horizon":         horizon_years,
        },
    }
