from config import BADGE_RULES


def badge(val: float, metric: str) -> str:
    """Coloured emoji label based on BADGE_RULES thresholds."""
    for threshold, label in BADGE_RULES.get(metric, []):
        if threshold is None or val >= threshold:
            return label
    return ""


def format_market_cap(val) -> str:
    """Raw $ → readable string (M/B/T)."""
    if val is None or val == 0:
        return "N/A"
    try:
        val = float(val)
        if val >= 1e12: return f"${val / 1e12:.2f}T"
        if val >= 1e9:  return f"${val / 1e9:.1f}B"
        if val >= 1e6:  return f"${val / 1e6:.0f}M"
        return f"${val:,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_val(val, fmt: str = "{:.2f}", fallback: str = "N/A") -> str:
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


def fmt_currency(val, currency: str = "$") -> str:
    return fmt_val(val, f"{currency}{{:,.2f}}")


def natural_summary(m: dict, mpt: dict, benchmark: str, div_score: dict,
                    health: dict | None = None) -> str:
    """Natural-language paragraph — all values come from computed metrics."""
    has_mpt   = bool(mpt)
    alpha     = mpt.get("alpha_ann", 0) if has_mpt else 0
    perf_word = "surperformé" if alpha > 0 else "sous-performé"
    risk_word = "élevée" if m["vol"] > 0.22 else "modérée" if m["vol"] > 0.12 else "faible"
    dd_word   = "important" if abs(m["max_dd"]) > 0.25 else "acceptable" if abs(m["max_dd"]) > 0.12 else "contenu"

    parts = [
        f"**Performance** — Rendement total de **{m['total_ret']:+.1%}**, "
        f"CAGR de **{m['cagr']:+.1%}**.",
    ]
    if has_mpt:
        parts[-1] += (
            f" Le portefeuille a {perf_word} le benchmark {benchmark} "
            f"avec un alpha de **{alpha:+.1%}/an**."
        )
    parts += [
        f"**Risque** — Volatilité annualisée {risk_word} à **{m['vol']:.1%}**. "
        f"Le pire repli historique est {dd_word} à **{m['max_dd']:.1%}**.",
        f"**Efficience** — Sharpe : **{m['sharpe']:.2f}** ({badge(m['sharpe'], 'Sharpe')}), "
        f"Sortino : **{m['sortino']:.2f}** ({badge(m['sortino'], 'Sortino')}), "
        f"Calmar : **{m['calmar']:.2f}** ({badge(m['calmar'], 'Calmar')}).",
        f"**Diversification** — Score **{div_score['score']}/100** — {div_score['label']}.",
    ]
    if health:
        parts.insert(0,
            f"**Health Score** — **{health['score']}/100** — _{health['label']}_."
        )
    return "\n\n".join(parts)
