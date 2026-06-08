from config import BADGE_RULES


def badge(val: float, metric: str) -> str:
    """Return a coloured emoji label based on BADGE_RULES thresholds."""
    for threshold, label in BADGE_RULES.get(metric, []):
        if threshold is None or val >= threshold:
            return label
    return ""


def format_market_cap(val) -> str:
    """Format a raw dollar market-cap value into a readable string (M / B / T)."""
    if val is None or val == 0:
        return "N/A"
    try:
        val = float(val)
        if val >= 1e12:
            return f"${val / 1e12:.2f}T"
        if val >= 1e9:
            return f"${val / 1e9:.1f}B"
        if val >= 1e6:
            return f"${val / 1e6:.0f}M"
        return f"${val:,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_val(val, fmt: str = "{:.2f}", fallback: str = "N/A") -> str:
    """Safe formatter — returns fallback if val is None or NaN."""
    if val is None:
        return fallback
    try:
        import math
        if math.isnan(float(val)):
            return fallback
        return fmt.format(float(val))
    except (TypeError, ValueError):
        return fallback


def fmt_pct(val, decimals: int = 1, signed: bool = False) -> str:
    sign = "+" if signed else ""
    return fmt_val(val, f"{{:{sign}.{decimals}%}}")


def natural_summary(m: dict, mpt: dict, benchmark: str, div_score: dict) -> str:
    """Natural-language summary paragraph — all values come from computed metrics."""
    perf_word = "surperformé" if mpt["alpha_ann"] > 0 else "sous-performé"
    risk_word = "élevée" if m["vol"] > 0.22 else "modérée" if m["vol"] > 0.12 else "faible"
    dd_word   = "important" if abs(m["max_dd"]) > 0.25 else "acceptable" if abs(m["max_dd"]) > 0.12 else "contenu"

    return (
        f"**Performance** — Rendement total de **{m['total_ret']:+.1%}**, CAGR de **{m['cagr']:+.1%}**. "
        f"Le portefeuille a {perf_word} le benchmark {benchmark} "
        f"avec un alpha de **{mpt['alpha_ann']:+.1%}/an**.\n\n"
        f"**Risque** — Volatilité annualisée {risk_word} à **{m['vol']:.1%}**. "
        f"Le pire repli historique est {dd_word} à **{m['max_dd']:.1%}**.\n\n"
        f"**Efficience** — Sharpe : **{m['sharpe']:.2f}** ({badge(m['sharpe'], 'Sharpe')}), "
        f"Sortino : **{m['sortino']:.2f}** ({badge(m['sortino'], 'Sortino')}), "
        f"Calmar : **{m['calmar']:.2f}** ({badge(m['calmar'], 'Calmar')}).\n\n"
        f"**Diversification** — Score **{div_score['score']}/100** — {div_score['label']}."
    )
