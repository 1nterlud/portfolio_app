"""
Portfolio Health Score (0-100) — synthesizes Sharpe, Drawdown, Diversification, Alpha.
The single number an investor should look at first.
"""
from config import HEALTH_GOOD_THRESHOLD, HEALTH_AVERAGE_THRESHOLD


def calc_health_score(m: dict, mpt: dict | None, div_score: dict) -> dict:
    """
    Compute composite health score 0-100.

    Weights:
      40% — Sharpe (efficiency)
      25% — Drawdown control
      20% — Diversification
      15% — Alpha vs benchmark
    """
    # Sharpe → 0..100 (Sharpe of 2.0 = 100)
    sharpe = m.get("sharpe", 0)
    sharpe_score = max(0, min(100, sharpe * 50))

    # Drawdown → 0..100 (DD of -5% = 100, -50% = 0)
    max_dd = abs(m.get("max_dd", 0))
    dd_score = max(0, min(100, 100 - (max_dd * 200)))

    # Diversification — already 0..100
    div_pts = div_score.get("score", 0)

    # Alpha → 0..100 (+10%/yr = 100, -10% = 0)
    alpha = mpt.get("alpha_ann", 0) if mpt else 0
    alpha_score = max(0, min(100, 50 + alpha * 500))

    total = round(
        0.40 * sharpe_score + 0.25 * dd_score + 0.20 * div_pts + 0.15 * alpha_score
    )

    if total >= HEALTH_GOOD_THRESHOLD:
        label, color = "Excellent", "#29a352"
    elif total >= HEALTH_AVERAGE_THRESHOLD:
        label, color = "Correct", "#e67e00"
    else:
        label, color = "À surveiller", "#dc3545"

    return {
        "score":  total,
        "label":  label,
        "color":  color,
        "breakdown": {
            "Sharpe":          round(sharpe_score),
            "Drawdown":        round(dd_score),
            "Diversification": round(div_pts),
            "Alpha":           round(alpha_score),
        },
    }
