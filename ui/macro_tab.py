"""
Macro tab — FRED data: Fed Funds Rate, CPI, 10Y Treasury, Unemployment, VIX.
"""
import streamlit as st
from data.macro import fetch_all_macro, macro_available
from ui.charts import chart_macro_series
from utils.components import render_section_title, render_empty_state


def render_tab_macro() -> None:
    render_section_title("🌍", "Environnement Macro", "Source : FRED (Federal Reserve)")

    if not macro_available():
        render_empty_state(
            "Clé FRED manquante",
            "Ajoutez `FRED_API_KEY` dans `.streamlit/secrets.toml` "
            "ou dans les secrets Streamlit Cloud.",
            "🔑",
        )
        return

    with st.spinner("Chargement des données macro FRED..."):
        series = fetch_all_macro(years=3)

    available = {n: s for n, s in series.items() if not s.empty}
    if not available:
        st.warning("Impossible de récupérer les données FRED. Vérifiez votre clé API.")
        return

    # KPI snapshot — latest values
    cols = st.columns(len(available))
    labels = {
        "Fed Funds Rate":   ("Taux directeur", "%"),
        "Inflation (CPI)":  ("CPI (inflation)", "pts"),
        "10Y Treasury":     ("Taux 10 ans US", "%"),
        "Chômage US":        ("Chômage US",      "%"),
        "VIX":              ("VIX (volatilité)", "pts"),
    }
    for col, (name, s) in zip(cols, available.items()):
        last  = float(s.iloc[-1])
        prev  = float(s.iloc[-2]) if len(s) > 1 else last
        delta = last - prev
        lbl, unit = labels.get(name, (name, ""))
        col.metric(lbl, f"{last:.2f} {unit}", f"{delta:+.2f}")

    st.divider()
    st.plotly_chart(chart_macro_series(available), use_container_width=True)
    st.caption(
        "Données FRED (Federal Reserve Bank of St. Louis). "
        "Mise à jour : mensuelle pour CPI/FEDFUNDS/UNRATE, quotidienne pour DGS10 et VIX."
    )
