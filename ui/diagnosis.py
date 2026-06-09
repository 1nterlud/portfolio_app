"""
Portfolio Diagnosis tab — health score, diversification, alerts, strengths/risks/suggestions,
natural-language summary, and PDF export.
"""
import streamlit as st
import pandas as pd

from analytics.allocation import calc_diversification_score, concentration_alerts
from analytics.health_score import calc_health_score
from utils.formatting import natural_summary
from utils.components import (
    render_health_gauge, render_alert_banner, render_audit_caption,
    render_section_title,
)
try:
    from utils.pdf_report import build_pdf_report
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False
from ui.charts import chart_health_breakdown
from config import __version__


def build_diagnosis(m: dict, mpt: dict | None, div_score: dict) -> tuple:
    """Rule-based diagnosis. Returns (strengths, risks, suggestions)."""
    strengths, risks, suggestions = [], [], []
    mpt = mpt or {}

    if m["sharpe"] >= 1.0:
        strengths.append(f"Sharpe élevé ({m['sharpe']:.2f}) — bonne efficience risque/rendement")
    else:
        risks.append(f"Sharpe faible ({m['sharpe']:.2f}) — rendement insuffisant pour le risque pris")
        suggestions.append("Revoir les positions à faible rendement ajusté au risque")

    if abs(m["max_dd"]) < 0.20:
        strengths.append(f"Max Drawdown contenu ({m['max_dd']:.1%})")
    else:
        risks.append(f"Max Drawdown important ({m['max_dd']:.1%}) — forte exposition aux replis")
        suggestions.append("Envisager des actifs défensifs (obligations, or, secteurs stables)")

    alpha = mpt.get("alpha_ann")
    if alpha is not None:
        if alpha > 0.02:
            strengths.append(f"Alpha positif ({alpha:+.1%}/an) — vraie valeur ajoutée vs marché")
        elif alpha < 0:
            risks.append(f"Alpha négatif ({alpha:+.1%}/an) — sous-performance après ajustement au risque")
            suggestions.append("Identifier les positions qui pèsent sur l'alpha")

    if div_score["score"] >= 70:
        strengths.append(f"Bonne diversification (score {div_score['score']}/100)")
    else:
        risks.append(f"Diversification insuffisante (score {div_score['score']}/100)")
        suggestions.append("Ajouter des positions dans des secteurs sous-représentés vs S&P 500")

    beta = mpt.get("beta")
    if beta is not None:
        if beta > 1.30:
            risks.append(f"Bêta élevé ({beta:.2f}) — très sensible aux corrections de marché")
            suggestions.append("Intégrer des actifs à faible bêta (utilities, consumer defensive)")
        elif beta < 0.70:
            strengths.append(f"Faible bêta ({beta:.2f}) — portefeuille défensif")

    if m["vol"] > 0.25:
        risks.append(f"Volatilité élevée ({m['vol']:.1%}) — drawdowns potentiels importants")
        suggestions.append("Réduire l'exposition aux titres à forte volatilité individuelle")

    if m["calmar"] >= 1.0:
        strengths.append(f"Ratio Calmar solide ({m['calmar']:.2f}) — CAGR bien proportionné au DD")

    info_ratio = mpt.get("info_ratio")
    if info_ratio is not None:
        if info_ratio >= 0.5:
            strengths.append(f"Information Ratio sain ({info_ratio:.2f}) — alpha actif robuste")
        elif info_ratio < -0.2:
            risks.append(f"Information Ratio négatif ({info_ratio:.2f}) — coût d'opportunité vs passif")

    return strengths, risks, suggestions


def build_proactive_alerts(m: dict, mpt: dict | None, df_port: pd.DataFrame,
                            comp_df: pd.DataFrame) -> list[tuple]:
    """Top-of-page alerts. Returns [(tone, message), ...]."""
    alerts = []
    mpt = mpt or {}

    if abs(m["max_dd"]) > 0.30:
        alerts.append(("danger",
                       f"⚠️ Drawdown maximal historique de **{m['max_dd']:.1%}** — exposition élevée aux replis."))
    elif abs(m["max_dd"]) > 0.20:
        alerts.append(("warning",
                       f"📉 Drawdown maximal de **{m['max_dd']:.1%}** — surveiller la résilience."))

    if m["sharpe"] < 0.5 and m["sharpe"] > 0:
        alerts.append(("warning",
                       f"⚖️ Sharpe sous **0.5** — efficience risque/rendement à améliorer."))
    elif m["sharpe"] <= 0:
        alerts.append(("danger",
                       f"🔴 Sharpe **négatif** — le portefeuille sous-performe le risque sans risque."))

    # Concentration alerts → repackaged
    for msg in concentration_alerts(df_port, comp_df):
        alerts.append(("warning", f"🎯 {msg}"))

    if mpt.get("info_ratio") is not None and mpt["info_ratio"] < -0.3:
        alerts.append(("warning",
                       f"📊 Information Ratio très négatif ({mpt['info_ratio']:.2f}) — "
                       f"l'indice passif aurait été plus efficace."))

    return alerts[:6]


def render_diagnosis(
    m: dict,
    mpt: dict,
    df_port: pd.DataFrame,
    comp_df: pd.DataFrame,
    benchmark: str,
    portfolio_name: str = "Mon Portefeuille",
    total_val: float = 0.0,
    fetched_at = None,
) -> None:
    sector_w  = (comp_df.set_index("Secteur")["Portefeuille"]
                 if "Portefeuille" in comp_df.columns else pd.Series(dtype=float))
    div_score = calc_diversification_score(df_port.set_index("Symbol")["W"], sector_w)
    health    = calc_health_score(m, mpt, div_score)

    # ── Proactive alerts banner ───────────────────────────────────────────────
    render_alert_banner(build_proactive_alerts(m, mpt, df_port, comp_df))

    # ── Natural-language summary ──────────────────────────────────────────────
    render_section_title("📝", "Résumé automatique", "Analyse en langage naturel")
    st.markdown(natural_summary(m, mpt, benchmark, div_score, health))
    st.divider()

    # ── Health Score & Diversification ────────────────────────────────────────
    col_h, col_d, col_a = st.columns([1, 1, 2])

    with col_h:
        render_section_title("🏆", "Health Score", "Sur 100")
        render_health_gauge(health["score"], health["label"], health["color"])
        with st.expander("Décomposition du score"):
            st.plotly_chart(chart_health_breakdown(health["breakdown"]),
                            use_container_width=True)

    with col_d:
        render_section_title("🎯", "Diversification", "Allocation")
        render_health_gauge(div_score["score"], div_score["label"], div_score["color"])

    with col_a:
        render_section_title("⚠️", "Concentration", "Alertes actives")
        cc = concentration_alerts(df_port, comp_df)
        if cc:
            for msg in cc:
                st.warning(msg)
        else:
            st.success("✅ Aucune alerte de concentration détectée.")

    st.divider()

    # ── Strengths / Risks / Suggestions ──────────────────────────────────────
    strengths, risks, suggestions = build_diagnosis(m, mpt, div_score)
    c1, c2, c3 = st.columns(3)
    with c1:
        render_section_title("✅", "Points forts", "")
        for item in strengths or ["Analyse insuffisante."]:
            st.markdown(f"- {item}")
    with c2:
        render_section_title("🔴", "Risques", "")
        for item in risks or ["Aucun risque majeur identifié."]:
            st.markdown(f"- {item}")
    with c3:
        render_section_title("💡", "Suggestions", "")
        for item in suggestions or ["Continuer à monitorer le portefeuille."]:
            st.markdown(f"- {item}")

    st.divider()

    # ── PDF Export ───────────────────────────────────────────────────────────
    render_section_title("📑", "Rapport PDF", "Export complet du diagnostic")
    pos_list = []
    for _, row in df_port.iterrows():
        pos_list.append({
            "Symbol":  row.get("Symbol"),
            "Qty":     row.get("Qty"),
            "Prix":    row.get("Prix"),
            "Val":     row.get("Val"),
            "W":       row.get("W"),
            "Secteur": row.get("Secteur"),
        })

    if not _PDF_AVAILABLE:
        st.info(
            "📦 Export PDF désactivé — installez la dépendance manquante :\n\n"
            "```\npip install reportlab\n```"
        )
    else:
        try:
            pdf_bytes = build_pdf_report(
                portfolio_name = portfolio_name,
                total_val      = total_val,
                m              = m,
                mpt            = mpt or {},
                health         = health,
                div_score      = div_score,
                benchmark      = benchmark,
                positions      = pos_list,
                strengths      = strengths,
                risks          = risks,
                suggestions    = suggestions,
                version        = __version__,
            )
            st.download_button(
                "📥 Télécharger le rapport PDF complet",
                data=pdf_bytes,
                file_name="rapport_portfolio.pdf",
                mime="application/pdf",
                type="primary",
            )
        except Exception as e:
            st.error(f"Génération PDF impossible : {e}")

    if fetched_at:
        render_audit_caption("yfinance Adj Close", fetched_at)
