"""
Portfolio Diagnosis tab — diversification score, concentration alerts,
strengths/risks/suggestions, and natural-language summary.
"""
import streamlit as st
import pandas as pd

from analytics.allocation import calc_diversification_score, concentration_alerts
from utils.formatting import badge, natural_summary


def render_diagnosis(
    m: dict,
    mpt: dict,
    df_port: pd.DataFrame,
    comp_df: pd.DataFrame,
    benchmark: str,
) -> None:
    # ── Natural-language summary ──────────────────────────────────────────────
    sector_w   = comp_df.set_index("Secteur")["Portefeuille"] if "Portefeuille" in comp_df.columns else pd.Series(dtype=float)
    div_score  = calc_diversification_score(df_port.set_index("Symbol")["W"], sector_w)

    st.subheader("📝 Résumé automatique")
    st.markdown(natural_summary(m, mpt, benchmark, div_score))
    st.divider()

    # ── Diversification score + alerts ───────────────────────────────────────
    col_score, col_alerts = st.columns([1, 2])

    with col_score:
        st.subheader("🎯 Diversification")
        score = div_score["score"]
        color = div_score["color"]
        st.markdown(
            f"<h1 style='text-align:center;color:{color};'>"
            f"{score}<span style='font-size:0.5em'>/100</span></h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align:center;color:{color};font-weight:600;'>"
            f"{div_score['label']}</p>",
            unsafe_allow_html=True,
        )
        st.progress(score / 100)

    with col_alerts:
        st.subheader("⚠️ Alertes")
        alerts = concentration_alerts(df_port, comp_df)
        if alerts:
            for msg in alerts:
                st.warning(msg)
        else:
            st.success("✅ Aucune alerte de concentration détectée.")

    st.divider()

    # ── Strengths / Risks / Suggestions ──────────────────────────────────────
    strengths, risks, suggestions = _build_diagnosis(m, mpt, div_score)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("✅ Points forts")
        for item in strengths or ["Analyse insuffisante."]:
            st.markdown(f"- {item}")
    with c2:
        st.subheader("🔴 Risques")
        for item in risks or ["Aucun risque majeur identifié."]:
            st.markdown(f"- {item}")
    with c3:
        st.subheader("💡 Suggestions")
        for item in suggestions or ["Continuer à monitorer le portefeuille."]:
            st.markdown(f"- {item}")


def _build_diagnosis(m: dict, mpt: dict, div_score: dict) -> tuple:
    """Rule-based diagnosis. Returns (strengths, risks, suggestions)."""
    strengths, risks, suggestions = [], [], []

    # Sharpe
    if m["sharpe"] >= 1.0:
        strengths.append(f"Sharpe élevé ({m['sharpe']:.2f}) — bonne efficience risque/rendement")
    else:
        risks.append(f"Sharpe faible ({m['sharpe']:.2f}) — rendement insuffisant pour le risque pris")
        suggestions.append("Revoir les positions à faible rendement ajusté au risque")

    # Drawdown
    if abs(m["max_dd"]) < 0.20:
        strengths.append(f"Max Drawdown contenu ({m['max_dd']:.1%})")
    else:
        risks.append(f"Max Drawdown important ({m['max_dd']:.1%}) — forte exposition aux replis")
        suggestions.append("Envisager des actifs défensifs (obligations, or, secteurs stables)")

    # Alpha
    if mpt["alpha_ann"] > 0.02:
        strengths.append(f"Alpha positif ({mpt['alpha_ann']:+.1%}/an) — vraie valeur ajoutée vs marché")
    elif mpt["alpha_ann"] < 0:
        risks.append(f"Alpha négatif ({mpt['alpha_ann']:+.1%}/an) — sous-performance après ajustement au risque")
        suggestions.append("Identifier les positions qui pèsent sur l'alpha")

    # Diversification
    if div_score["score"] >= 70:
        strengths.append(f"Bonne diversification (score {div_score['score']}/100)")
    else:
        risks.append(f"Diversification insuffisante (score {div_score['score']}/100)")
        suggestions.append("Ajouter des positions dans des secteurs sous-représentés vs S&P 500")

    # Beta
    if mpt["beta"] > 1.30:
        risks.append(f"Bêta élevé ({mpt['beta']:.2f}) — très sensible aux corrections de marché")
        suggestions.append("Intégrer des actifs à faible bêta (ex : utilities, consumer defensive)")
    elif mpt["beta"] < 0.70:
        strengths.append(f"Faible bêta ({mpt['beta']:.2f}) — portefeuille défensif")

    # Volatility
    if m["vol"] > 0.25:
        risks.append(f"Volatilité élevée ({m['vol']:.1%}) — drawdowns potentiels importants")
        suggestions.append("Réduire l'exposition aux titres à forte volatilité individuelle")

    # Calmar
    if m["calmar"] >= 1.0:
        strengths.append(f"Ratio Calmar solide ({m['calmar']:.2f}) — CAGR bien proportionné au drawdown subi")

    return strengths, risks, suggestions
