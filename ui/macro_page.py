"""
Macro page — standalone macro environment dashboard (FRED).
Independent from any portfolio: rates & yield curve, inflation,
real economy, markets, plus a rule-based French interpretation.
"""
import streamlit as st
import pandas as pd

from data.macro import fetch_macro_category, macro_available, MACRO_CATALOG
from analytics.macro_signals import macro_signals, yoy_change
from ui.charts import chart_macro_lines
from utils.components import (
    render_page_hero, render_empty_state, render_section_title,
    render_alert_banner,
)

_TONE_ICON = {"danger": "🔴", "warning": "🟠", "success": "🟢", "info": "🔵"}


def render_macro(inputs: dict) -> None:
    render_page_hero(
        eyebrow="Environnement macro",
        title="Macro Dashboard",
        subtitle="Taux, courbe des rendements, inflation, économie réelle et stress de "
                 "marché — indépendant de votre portefeuille.",
        pills=[("🏦", "Taux & Courbe"), ("📈", "Inflation"),
               ("🏭", "Économie réelle"), ("🌪️", "Marchés")],
    )

    if not macro_available():
        render_empty_state(
            "Clé FRED manquante",
            "Cette page utilise l'API gratuite de la Federal Reserve (FRED). "
            "Créez une clé sur fred.stlouisfed.org puis ajoutez `FRED_API_KEY` "
            "dans `.streamlit/secrets.toml` (local) ou dans les Secrets Streamlit Cloud.",
            "🔑",
        )
        return

    years = st.radio("Période", [3, 5, 10], index=1, horizontal=True,
                     format_func=lambda y: f"{y} ans")

    with st.spinner("Chargement des données FRED..."):
        data = {cat: fetch_macro_category(cat, years) for cat in MACRO_CATALOG}

    all_series = {k: v for cat in data.values() for k, v in cat.items()}
    if not any(not s.empty for s in all_series.values()):
        st.warning("Impossible de récupérer les données FRED. "
                   "Vérifiez votre clé API ou réessayez plus tard.")
        return

    # ── Lecture macro (rule-based signals) ───────────────────────────────────
    signals = macro_signals(all_series)
    if signals:
        render_section_title("🧭", "Lecture macro", "Interprétation automatique")
        render_alert_banner([(s["tone"], f"{_TONE_ICON.get(s['tone'], '')} "
                              f"**{s['title']}** — {s['message']}") for s in signals])
        st.divider()

    # ── Snapshot KPIs ─────────────────────────────────────────────────────────
    render_section_title("📌", "Snapshot", "Dernières valeurs publiées")
    kpis = []
    for cat, series in data.items():
        for label, s in series.items():
            s = s.dropna()
            if s.empty:
                continue
            unit = MACRO_CATALOG[cat][label][1]
            last = float(s.iloc[-1])
            prev = float(s.iloc[-2]) if len(s) > 1 else last
            kpis.append((label, last, last - prev, unit))

    for row_start in range(0, len(kpis), 4):
        cols = st.columns(4)
        for col, (label, last, delta, unit) in zip(cols, kpis[row_start:row_start + 4]):
            suffix = f" {unit}" if unit != "idx" else ""
            col.metric(label, f"{last:,.2f}{suffix}", f"{delta:+.2f}")

    st.divider()

    # ── Detail tabs per category ──────────────────────────────────────────────
    tab_rates, tab_infl, tab_real, tab_mkt = st.tabs(
        ["🏦 Taux & Courbe", "📈 Inflation", "🏭 Économie réelle", "🌪️ Marchés"]
    )

    with tab_rates:
        rates = data["Taux & Courbe"]
        curve = {k: rates[k] for k in ("Fed Funds Rate", "Treasury 2 ans",
                                       "Treasury 10 ans", "Mortgage 30 ans")
                 if k in rates and not rates[k].empty}
        if curve:
            st.plotly_chart(chart_macro_lines(curve, "Taux directeurs et de marché",
                                              y_title="%"),
                            use_container_width=True)
        spread = rates.get("Spread 10a − 2a", pd.Series(dtype=float))
        if not spread.empty:
            st.plotly_chart(chart_macro_lines({"Spread 10a − 2a": spread},
                                              "Courbe des taux : spread 10 ans − 2 ans",
                                              y_title="pt", hline=0.0),
                            use_container_width=True)
            st.caption("Sous la ligne 0 = courbe inversée. Chaque récession US depuis "
                       "1976 a été précédée d'une inversion prolongée de la courbe.")

    with tab_infl:
        infl = data["Inflation"]
        yoy = {}
        for label, s in infl.items():
            y = yoy_change(s).dropna()
            if not y.empty:
                yoy[label.replace("(indice)", "YoY")] = y
        if yoy:
            st.plotly_chart(chart_macro_lines(yoy, "Inflation en glissement annuel",
                                              y_title="%", hline=2.0),
                            use_container_width=True)
            st.caption("Ligne pointillée = cible Fed de 2%. Le Core CPI exclut "
                       "énergie et alimentation (composantes volatiles).")
        else:
            st.info("Données d'inflation indisponibles.")

    with tab_real:
        real = data["Économie réelle"]
        un = real.get("Chômage US", pd.Series(dtype=float))
        if not un.empty:
            st.plotly_chart(chart_macro_lines({"Chômage US": un},
                                              "Taux de chômage US", y_title="%"),
                            use_container_width=True)
        c1, c2 = st.columns(2)
        gdp = real.get("Croissance PIB réel", pd.Series(dtype=float))
        if not gdp.empty:
            with c1:
                st.plotly_chart(chart_macro_lines({"PIB réel (T/T annualisé)": gdp},
                                                  "Croissance du PIB réel",
                                                  y_title="%", hline=0.0),
                                use_container_width=True)
        sent = real.get("Sentiment conso (UMich)", pd.Series(dtype=float))
        if not sent.empty:
            with c2:
                st.plotly_chart(chart_macro_lines({"Sentiment consommateur": sent},
                                                  "Sentiment consommateur (UMichigan)",
                                                  y_title="indice"),
                                use_container_width=True)

    with tab_mkt:
        mkt = data["Marchés"]
        vix = mkt.get("VIX", pd.Series(dtype=float))
        if not vix.empty:
            st.plotly_chart(chart_macro_lines({"VIX": vix},
                                              "VIX — volatilité implicite S&P 500",
                                              y_title="pt", hline=20.0),
                            use_container_width=True)
            st.caption("Au-dessus de 20 = nervosité, au-dessus de 30 = stress élevé. "
                       "Moyenne historique ~19.")
        usd = mkt.get("Dollar Index (broad)", pd.Series(dtype=float))
        if not usd.empty:
            st.plotly_chart(chart_macro_lines({"Dollar Index": usd},
                                              "Dollar US (indice large, pondéré commerce)",
                                              y_title="indice"),
                            use_container_width=True)
            st.caption("Dollar fort = vent contraire pour les résultats des "
                       "multinationales US et les marchés émergents.")

    st.caption("Source : FRED, Federal Reserve Bank of St. Louis. "
               "Données en cache 1 h — bouton 🔄 dans la sidebar pour forcer le rechargement.")
