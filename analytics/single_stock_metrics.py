"""
Single-stock fundamental analytics:
  - Piotroski F-Score (9 true criteria)
  - Quality Rating (computed from fundamentals)
  - Stock badges (Value/Growth, Dividend, Risk, Size, etc.)
"""
import pandas as pd
from config import QUALITY_HIGH_THRESHOLD, QUALITY_AVERAGE_THRESHOLD, PIOTROSKI_STRONG, PIOTROSKI_NEUTRAL


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get(df: pd.DataFrame, *names, col: int = 0):
    """Try multiple row-name variants; return float or None."""
    for name in names:
        if name in df.index:
            try:
                val = df.loc[name].iloc[col]
                return float(val) if val is not None else None
            except (IndexError, TypeError, ValueError):
                pass
    return None


# ── Piotroski F-Score ─────────────────────────────────────────────────────────

def calc_piotroski(financials: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame) -> dict:
    """
    Compute the 9-point Piotroski F-Score.

    Returns {"score": int, "details": {criterion: 0|1}, "available": bool}.
    If essential data is missing, returns available=False.

    Criteria:
      Profitability (4):  F1 ROA>0 | F2 OCF>0 | F3 ΔROA↑ | F4 OCF>NI (accrual)
      Leverage     (3):  F5 LT Debt↓ | F6 Current Ratio↑ | F7 No dilution
      Efficiency   (2):  F8 Gross Margin↑ | F9 Asset Turnover↑
    """
    result = {"score": None, "details": {}, "available": False}

    if financials.empty or balance.empty or cashflow.empty:
        return result
    if financials.shape[1] < 2 or balance.shape[1] < 2:
        return result

    try:
        # ── Base data ──────────────────────────────────────────────────────────
        net_inc_0 = _get(financials, "Net Income")
        net_inc_1 = _get(financials, "Net Income", col=1)
        ta_0      = _get(balance, "Total Assets")
        ta_1      = _get(balance, "Total Assets", col=1)
        ocf       = _get(cashflow, "Operating Cash Flow", "Cash Flow From Operations")

        # Without these we can't compute anything meaningful
        if any(v is None for v in [net_inc_0, ta_0, ocf, ta_1, net_inc_1]):
            return result

        roa_0 = net_inc_0 / ta_0
        roa_1 = net_inc_1 / ta_1

        # ── Profitability ──────────────────────────────────────────────────────
        f1 = int(roa_0 > 0)
        f2 = int(ocf > 0)
        f3 = int(roa_0 > roa_1)
        f4 = int((ocf / ta_0) > roa_0)   # cash earnings quality

        # ── Leverage & liquidity ──────────────────────────────────────────────
        ltd_0  = _get(balance, "Long Term Debt", "Long-Term Debt")
        ltd_1  = _get(balance, "Long Term Debt", "Long-Term Debt", col=1)
        if ltd_0 is not None and ltd_1 is not None:
            f5 = int((ltd_0 / ta_0) < (ltd_1 / ta_1))
        else:
            f5 = 0

        ca_0 = _get(balance, "Current Assets")
        cl_0 = _get(balance, "Current Liabilities", "Current Liabilities Net Minority Interest")
        ca_1 = _get(balance, "Current Assets", col=1)
        cl_1 = _get(balance, "Current Liabilities", "Current Liabilities Net Minority Interest", col=1)
        if all(v is not None and v != 0 for v in [ca_0, cl_0, ca_1, cl_1]):
            f6 = int((ca_0 / cl_0) > (ca_1 / cl_1))
        else:
            f6 = 0

        sh_0 = _get(balance, "Ordinary Shares Number", "Share Issued", "Common Stock")
        sh_1 = _get(balance, "Ordinary Shares Number", "Share Issued", "Common Stock", col=1)
        f7 = int(sh_0 <= sh_1) if (sh_0 is not None and sh_1 is not None) else 0

        # ── Operating efficiency ───────────────────────────────────────────────
        rev_0  = _get(financials, "Total Revenue", "Revenue")
        rev_1  = _get(financials, "Total Revenue", "Revenue", col=1)
        gp_0   = _get(financials, "Gross Profit")
        gp_1   = _get(financials, "Gross Profit", col=1)
        if all(v is not None and v != 0 for v in [rev_0, rev_1, gp_0, gp_1]):
            f8 = int((gp_0 / rev_0) > (gp_1 / rev_1))
            f9 = int((rev_0 / ta_0) > (rev_1 / ta_1))
        else:
            f8 = f9 = 0

        score = f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8 + f9
        details = {
            "F1 — ROA > 0":              f1,
            "F2 — OCF > 0":              f2,
            "F3 — ROA en hausse":        f3,
            "F4 — Qualité du cash":      f4,
            "F5 — Levier en baisse":     f5,
            "F6 — Liquidité en hausse":  f6,
            "F7 — Pas de dilution":      f7,
            "F8 — Marge brute en hausse": f8,
            "F9 — Rotation actifs ↑":    f9,
        }
        return {"score": score, "details": details, "available": True}

    except Exception:
        return result


# ── Quality Rating ────────────────────────────────────────────────────────────

def calc_quality_rating(info: dict) -> dict | None:
    """
    Compute a quality score 0–100 from available fundamental data.
    Returns None if insufficient data (< 3 datapoints available).

    Dimensions: profit margin, ROE, debt/equity, FCF yield, revenue growth.
    """
    points, max_pts = 0, 0

    def _score(val, thresholds: list[tuple]) -> tuple[int, int]:
        """Return (earned, possible) points for a value against ordered thresholds."""
        if val is None:
            return 0, 0
        possible = thresholds[0][1]
        for threshold, pts in thresholds:
            if val >= threshold:
                return pts, possible
        return 0, possible

    # Profit margin (net)
    pm = info.get("profitMargins")
    p, m = _score(pm, [(0.20, 20), (0.10, 15), (0.05, 10), (0.0, 5)])
    points += p; max_pts += m

    # Return on Equity
    roe = info.get("returnOnEquity")
    p, m = _score(roe, [(0.20, 20), (0.12, 15), (0.05, 10), (0.0, 5)])
    points += p; max_pts += m

    # Debt / Equity (lower = better → invert thresholds)
    de_raw = info.get("debtToEquity")
    if de_raw is not None:
        # yfinance returns D/E as a ratio (e.g. 1.5 = 150%)
        de = de_raw / 100 if de_raw > 10 else de_raw
        max_pts += 20
        if de < 0.3:   points += 20
        elif de < 0.7: points += 15
        elif de < 1.5: points += 10
        elif de < 3.0: points += 5

    # FCF Yield
    fcf  = info.get("freeCashflow")
    mcap = info.get("marketCap")
    if fcf is not None and mcap and mcap > 0:
        fcf_y = fcf / mcap
        p, m = _score(fcf_y, [(0.06, 20), (0.03, 15), (0.0, 10)])
        points += p; max_pts += m

    # Revenue growth YoY
    rev_g = info.get("revenueGrowth")
    p, m = _score(rev_g, [(0.20, 20), (0.10, 15), (0.05, 10), (0.0, 5)])
    points += p; max_pts += m

    if max_pts < 40:   # too little data
        return None

    score = round(points / max_pts * 100)
    if score >= QUALITY_HIGH_THRESHOLD:
        label, color = "High Quality", "green"
    elif score >= QUALITY_AVERAGE_THRESHOLD:
        label, color = "Average Quality", "orange"
    else:
        label, color = "Low Quality", "red"

    return {"score": score, "label": label, "color": color}


# ── Stock Badges ──────────────────────────────────────────────────────────────

def get_stock_badges(info: dict, quality: dict | None = None, piotroski_score: int | None = None) -> list[tuple]:
    """
    Return a list of (label, color) badge tuples describing the stock's characteristics.
    Colors are Streamlit color names: green, blue, red, orange, gray, violet.
    """
    badges = []
    pe_fwd   = info.get("forwardPE")
    pe_trail = info.get("trailingPE")
    div_y    = info.get("dividendYield") or 0
    beta     = info.get("beta")
    rev_g    = info.get("revenueGrowth") or 0
    mcap     = info.get("marketCap") or 0
    de_raw   = info.get("debtToEquity")

    # Style (Value / Blend / Growth)
    pe = pe_fwd or pe_trail
    if pe and pe > 0:
        if pe < 15:     badges.append(("💰 Value",  "blue"))
        elif pe > 35:   badges.append(("🚀 Growth", "violet"))
        else:            badges.append(("⚖️ Blend",  "gray"))

    # Dividend
    if div_y > 0.03:
        badges.append((f"💵 Dividende {div_y:.1%}", "green"))
    elif div_y > 0:
        badges.append((f"💵 Dividende {div_y:.1%}", "gray"))

    # Risk
    if beta is not None:
        if beta > 1.5:   badges.append(("⚠️ High Risk", "red"))
        elif beta < 0.7: badges.append(("🛡️ Défensif",  "green"))

    # Leverage
    if de_raw is not None:
        de = de_raw / 100 if de_raw > 10 else de_raw
        if de > 2.0:  badges.append(("🔴 Levier Élevé", "red"))

    # Quality
    if quality:
        if quality["score"] >= QUALITY_HIGH_THRESHOLD:
            badges.append(("⭐ High Quality", "green"))
        elif quality["score"] < QUALITY_AVERAGE_THRESHOLD:
            badges.append(("⚠️ Low Quality", "red"))

    # Piotroski
    if piotroski_score is not None:
        if piotroski_score >= PIOTROSKI_STRONG:
            badges.append((f"✅ Piotroski {piotroski_score}/9", "green"))
        elif piotroski_score < 4:
            badges.append((f"🔴 Piotroski {piotroski_score}/9", "red"))

    # Size
    if mcap >= 200e9:   badges.append(("🏢 Mega Cap",  "gray"))
    elif mcap >= 10e9:  badges.append(("🏬 Large Cap", "gray"))
    elif mcap >= 2e9:   badges.append(("🏪 Mid Cap",   "gray"))
    elif mcap > 0:      badges.append(("🏠 Small Cap", "gray"))

    return badges
