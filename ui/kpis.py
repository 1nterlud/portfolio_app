import streamlit as st
from utils.formatting import badge


def render_kpis(m: dict, total_val: float) -> None:
    """Render the top KPI bar — always visible above the tabs."""
    st.markdown(f"### Valeur Totale : `${total_val:,.0f}`")

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Rendement Total", f"{m['total_ret']:+.1%}")
    k2.metric("CAGR",            f"{m['cagr']:+.1%}")
    k3.metric("Volatilité Ann.", f"{m['vol']:.1%}")
    k4.metric("Sharpe",          f"{m['sharpe']:.2f}")
    k5.metric("Sortino",         f"{m['sortino']:.2f}")
    k6.metric("Max Drawdown",    f"{m['max_dd']:.1%}")

    b1, b2, b3 = st.columns(3)
    b1.caption(f"Sharpe  : {badge(m['sharpe'],  'Sharpe')}")
    b2.caption(f"Sortino : {badge(m['sortino'], 'Sortino')}")
    b3.caption(f"Calmar  : {badge(m['calmar'],  'Calmar')}  ({m['calmar']:.2f})")
