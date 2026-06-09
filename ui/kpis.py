import streamlit as st
from utils.formatting import badge
from utils.components import (
    render_hero_value, render_health_gauge, render_audit_caption,
    render_section_title, render_badges,
)


def render_hero(total_val: float, m: dict, health: dict, fetched_at=None,
                n_days: int = 0) -> None:
    """Top hero block — gradient value card + health gauge side by side."""
    delta_tone = "success" if m["total_ret"] >= 0 else "danger"
    delta_str  = f"{m['total_ret']:+.1%} depuis le début"

    col_val, col_health = st.columns([2, 1])
    with col_val:
        render_hero_value("Valeur Totale du Portefeuille",
                          f"${total_val:,.0f}", delta_str, delta_tone)
    with col_health:
        render_health_gauge(health["score"], health["label"], health["color"])

    if fetched_at or n_days:
        render_audit_caption("yfinance · Adj Close", fetched_at, n_days=n_days)


def render_kpis(m: dict, mpt: dict | None = None) -> None:
    """Secondary KPI strip below the hero — performance + MPT metrics."""
    render_section_title("📊", "Métriques de performance",
                         "Sur la période sélectionnée")

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("CAGR",            f"{m['cagr']:+.1%}")
    k2.metric("Volatilité Ann.", f"{m['vol']:.1%}")
    k3.metric("Sharpe",          f"{m['sharpe']:.2f}")
    k4.metric("Sortino",         f"{m['sortino']:.2f}")
    k5.metric("Max Drawdown",    f"{m['max_dd']:.1%}")
    k6.metric("Calmar",          f"{m['calmar']:.2f}")

    if mpt:
        st.write("")
        render_section_title("🎯", "Statistiques MPT",
                             "vs benchmark sélectionné")
        i1, i2, i3, i4 = st.columns(4)
        i1.metric("Beta",         f"{mpt['beta']:.2f}")
        i2.metric("Alpha Ann.",   f"{mpt['alpha_ann']:+.1%}")
        i3.metric("Info Ratio",   f"{mpt.get('info_ratio', 0):.2f}")
        i4.metric("Tracking Err", f"{mpt.get('tracking_error', 0):.1%}")

    # Badge row (ratings)
    sharpe_lbl  = badge(m['sharpe'],  'Sharpe')
    sortino_lbl = badge(m['sortino'], 'Sortino')
    calmar_lbl  = badge(m['calmar'],  'Calmar')

    pills = [
        (f"Sharpe : {sharpe_lbl}",   _tone_from_badge(sharpe_lbl)),
        (f"Sortino : {sortino_lbl}", _tone_from_badge(sortino_lbl)),
        (f"Calmar : {calmar_lbl}",   _tone_from_badge(calmar_lbl)),
    ]
    render_badges(pills)


def _tone_from_badge(label: str) -> str:
    """Convert badge emoji-label into a tone key."""
    if "🟢" in label or "Excellent" in label or "Solide" in label: return "success"
    if "🔵" in label or "Bon" in label:                            return "info"
    if "🟡" in label or "Moyen" in label:                          return "warning"
    if "🔴" in label or "Faible" in label or "Fragile" in label:   return "danger"
    return "neutral"
