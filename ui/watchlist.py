"""
Watchlist — quick-glance pricing + sparkline for tickers you're tracking.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data.single_stock import fetch_stock_info, fetch_stock_history
from data.normalize import normalize_stock_info
from utils.components import (
    render_empty_state, render_page_hero, render_section_title,
)
from utils.formatting import fmt_val, fmt_pct
from config import COLORS


def _parse_tickers(raw: str) -> list[str]:
    out = []
    seen = set()
    for line in raw.replace("\n", ",").replace(";", ",").split(","):
        t = line.strip().upper()
        if t and t not in seen:
            out.append(t)
            seen.add(t)
    return out[:20]


def _sparkline(close: pd.Series) -> go.Figure:
    if close.empty:
        return go.Figure()
    up_trend = close.iloc[-1] >= close.iloc[0]
    color = COLORS["success"] if up_trend else COLORS["danger"]
    fill  = "rgba(16, 185, 129, 0.12)" if up_trend else "rgba(244, 63, 94, 0.12)"
    fig = go.Figure(go.Scatter(
        x=close.index, y=close.values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=fill,
        hoverinfo="skip",
    ))
    fig.update_layout(
        height=58,
        margin=dict(t=2, b=2, l=2, r=2),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def render_watchlist(inputs: dict) -> None:
    render_page_hero(
        eyebrow="Liste de suivi",
        title="Watchlist",
        subtitle="Coup d'œil rapide sur vos tickers suivis — prix, performance 30 jours, sparkline.",
        pills=[("👁️", "Suivi temps réel"), ("📈", "Performance 30j"), ("✨", "Sparkline")],
    )

    tickers = _parse_tickers(inputs.get("tickers_raw", ""))
    if not tickers:
        render_empty_state(
            "Watchlist vide",
            "Ajoutez quelques tickers dans le panneau gauche pour commencer.",
            "👁️",
        )
        return

    with st.spinner(f"Chargement de {len(tickers)} tickers..."):
        rows = []
        for t in tickers:
            info = fetch_stock_info(t)
            if not info:
                continue
            snap = normalize_stock_info(t, info)
            hist = fetch_stock_history(t, "1mo")
            close = hist["Close"] if not hist.empty else pd.Series(dtype=float)
            perf_30 = (close.iloc[-1] / close.iloc[0] - 1) if len(close) > 1 else None
            rows.append({
                "ticker": t,
                "name":   snap.name,
                "sector": snap.sector,
                "price":  snap.price,
                "perf_30": perf_30,
                "spark":  close,
            })

    if not rows:
        render_empty_state("Aucun ticker chargé", "Vérifiez l'orthographe.", "👁️")
        return

    render_section_title("📋", "Vos tickers",
                         f"{len(rows)} valeur{'s' if len(rows) > 1 else ''} suivie{'s' if len(rows) > 1 else ''}")

    # Header
    h1, h2, h3, h4, h5 = st.columns([1.2, 2.5, 1.2, 1.2, 2])
    h1.markdown("**Ticker**")
    h2.markdown("**Nom · Secteur**")
    h3.markdown("**Prix**")
    h4.markdown("**30j**")
    h5.markdown("**Sparkline**")
    st.divider()

    for r in rows:
        c1, c2, c3, c4, c5 = st.columns([1.2, 2.5, 1.2, 1.2, 2])
        c1.markdown(f"**{r['ticker']}**")
        c2.markdown(f"{r['name']}  \n_{r['sector']}_")
        c3.markdown(fmt_val(r["price"], "${:,.2f}"))
        if r["perf_30"] is not None:
            up = r["perf_30"] >= 0
            color = COLORS["success"] if up else COLORS["danger"]
            arrow = "▲" if up else "▼"
            c4.markdown(
                f"<span style='color:{color};font-weight:700'>"
                f"{arrow} {r['perf_30']:+.1%}</span>",
                unsafe_allow_html=True,
            )
        else:
            c4.markdown("—")
        with c5:
            st.plotly_chart(_sparkline(r["spark"]),
                            use_container_width=True,
                            config={"displayModeBar": False})
