"""
Compare 2–4 stocks side by side: price perf, valuation, margins, quality.
"""
import streamlit as st
import pandas as pd

from data.single_stock import fetch_stock_info, fetch_stock_history
from data.normalize import normalize_stock_info
from analytics.single_stock_metrics import calc_quality_rating
from ui.charts import chart_compare_metric
from utils.components import (
    render_empty_state, render_kv_table,
    render_page_hero, render_section_title,
)
from utils.formatting import fmt_pct, fmt_val, format_market_cap


def _parse_tickers(raw: str) -> list[str]:
    out = []
    for t in raw.replace(";", ",").split(","):
        t = t.strip().upper()
        if t and t not in out:
            out.append(t)
    return out[:4]


def render_compare(inputs: dict) -> None:
    render_page_hero(
        eyebrow="Comparaison multi-actions",
        title="Compare Stocks",
        subtitle="Confrontation côte à côte de 2 à 4 titres — valorisation, qualité, performance.",
        pills=[("📊", "Valorisation"), ("💰", "Marges & ROE"),
               ("📈", "Performance 1 an"), ("🏆", "Quality rating")],
    )

    if not inputs.get("run"):
        render_empty_state(
            "Aucune comparaison lancée",
            "Entrez 2 à 4 tickers (ex: AAPL, MSFT, GOOGL) dans le panneau gauche puis cliquez Comparer →.",
            "⚖️",
        )
        return

    tickers = _parse_tickers(inputs.get("tickers_raw", ""))
    if len(tickers) < 2:
        st.warning("Veuillez fournir au moins 2 tickers valides.")
        return

    snaps = []
    qualities = []
    histories = {}
    with st.spinner(f"Chargement de {', '.join(tickers)}..."):
        for t in tickers:
            raw = fetch_stock_info(t)
            if not raw:
                continue
            snaps.append(normalize_stock_info(t, raw))
            qualities.append(calc_quality_rating(raw))
            hist = fetch_stock_history(t, "1y")
            if not hist.empty:
                histories[t] = hist["Close"]

    if not snaps:
        render_empty_state("Aucun ticker valide", "Vérifiez l'orthographe.", "🔎")
        return

    # ── Side-by-side cards ───────────────────────────────────────────────────
    render_section_title("🎴", "Cartes synthèse",
                         f"{len(snaps)} ticker{'s' if len(snaps) > 1 else ''}")
    cols = st.columns(len(snaps))
    for col, snap, qual in zip(cols, snaps, qualities):
        with col:
            st.subheader(snap.ticker)
            st.caption(snap.name)
            render_kv_table([
                ("Prix",         fmt_val(snap.price, "${:,.2f}")),
                ("Market Cap",   format_market_cap(snap.market_cap)),
                ("Secteur",      snap.sector),
                ("P/E fwd",      fmt_val(snap.pe_forward, "{:.1f}x")),
                ("EV/EBITDA",    fmt_val(snap.ev_ebitda,  "{:.1f}x")),
                ("ROE",          fmt_pct(snap.roe)),
                ("Marge nette",  fmt_pct(snap.profit_margin)),
                ("Div. Yield",   fmt_pct(snap.div_yield, decimals=2)),
                ("Beta",         fmt_val(snap.beta, "{:.2f}")),
            ])
            if qual:
                color = qual["color"]
                st.markdown(
                    f"<div style='text-align:center;padding:6px;border-radius:8px;"
                    f"background:#f8fafc;margin-top:6px'>"
                    f"<b style='color:{color}'>{qual['label']} — {qual['score']}/100</b>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.divider()
    render_section_title("📊", "Comparatif graphique",
                         "Valorisation, marges et performance")

    # ── Comparison charts ────────────────────────────────────────────────────
    rows_pe   = [{"Symbol": s.ticker, "metric": s.pe_forward} for s in snaps]
    rows_roe  = [{"Symbol": s.ticker, "metric": s.roe}        for s in snaps]
    rows_marg = [{"Symbol": s.ticker, "metric": s.profit_margin} for s in snaps]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Forward P/E")
        st.plotly_chart(
            chart_compare_metric(
                [{"Symbol": r["Symbol"], "P/E fwd": r["metric"]} for r in rows_pe
                 if r["metric"] is not None],
                "P/E fwd",
            ),
            use_container_width=True,
        )
    with c2:
        st.subheader("ROE")
        st.plotly_chart(
            chart_compare_metric(
                [{"Symbol": r["Symbol"], "ROE": r["metric"]} for r in rows_roe
                 if r["metric"] is not None],
                "ROE", format_pct=True,
            ),
            use_container_width=True,
        )

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Marge nette")
        st.plotly_chart(
            chart_compare_metric(
                [{"Symbol": r["Symbol"], "Marge nette": r["metric"]} for r in rows_marg
                 if r["metric"] is not None],
                "Marge nette", format_pct=True,
            ),
            use_container_width=True,
        )
    with c4:
        st.subheader("Performance 1 an (rebased à 100)")
        if histories:
            df = pd.DataFrame(histories).dropna()
            if not df.empty:
                norm = (df / df.iloc[0]) * 100
                st.line_chart(norm)
            else:
                st.caption("_Données de prix incomplètes._")
        else:
            st.caption("_Pas d'historique disponible._")
