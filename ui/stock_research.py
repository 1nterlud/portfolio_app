"""
Stock Research page — complete single-ticker fundamental analysis.
Independent of the portfolio: the user can open this page without any positions.
"""
import streamlit as st
import pandas as pd

from data.single_stock import fetch_stock_info, fetch_stock_history, fetch_stock_financials
from analytics.single_stock_metrics import calc_piotroski, calc_quality_rating, get_stock_badges
from ui.charts import chart_price_history, chart_revenue_net_income, chart_eps
from utils.formatting import format_market_cap, fmt_val, fmt_pct


# ── Entry point ───────────────────────────────────────────────────────────────

def render_stock_research(ticker: str = "AAPL", analyze: bool = False) -> None:
    """Render the complete stock research page."""

    st.markdown("## 🔍 Stock Research")
    st.caption("Analyse fondamentale d'un titre — indépendante du portefeuille.")

    if not analyze:
        st.info("Entrez un ticker dans le panneau gauche et cliquez sur **Analyser →**.")
        return

    if not ticker:
        st.warning("Veuillez entrer un ticker valide.")
        return

    with st.spinner(f"Analyse de **{ticker}** en cours..."):
        info      = fetch_stock_info(ticker)
        stmts     = fetch_stock_financials(ticker)

    if not info:
        st.error(
            f"❌ Ticker **{ticker}** introuvable ou sans données disponibles. "
            "Vérifiez l'orthographe (ex: AAPL, MSFT, ASML.AS)."
        )
        return

    # Pre-compute quality metrics
    quality   = calc_quality_rating(info)
    piotroski = calc_piotroski(stmts["financials"], stmts["balance_sheet"], stmts["cashflow"])
    p_score   = piotroski["score"] if piotroski["available"] else None
    badges    = get_stock_badges(info, quality, p_score)

    # ── Header ────────────────────────────────────────────────────────────────
    _render_header(ticker, info, badges)
    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tabs = st.tabs(["📈 Prix & Profil", "📊 Valorisation & Qualité",
                    "💰 Résultats Financiers", "🏦 Bilan & Analystes"])

    with tabs[0]: _tab_price_profile(ticker, info)
    with tabs[1]: _tab_valuation_quality(info, quality, piotroski)
    with tabs[2]: _tab_financials(stmts)
    with tabs[3]: _tab_balance_analysts(info)


# ── Header ─────────────────────────────────────────────────────────────────────

def _render_header(ticker: str, info: dict, badges: list) -> None:
    name  = info.get("longName") or info.get("shortName") or ticker
    price = info.get("currentPrice") or info.get("regularMarketPreviousClose")
    chg   = info.get("regularMarketChangePercent")

    col_logo, col_title, col_price = st.columns([0.6, 3, 2])

    with col_logo:
        logo = info.get("logo_url")
        if logo:
            try:
                st.image(logo, width=64)
            except Exception:
                pass

    with col_title:
        st.markdown(f"### {name}")
        st.caption(
            f"{ticker}  ·  {info.get('sector', 'N/A')}  ·  {info.get('industry', 'N/A')}  "
            f"·  {info.get('exchange', '')}"
        )

    with col_price:
        if price:
            delta_str = f"{chg:+.2%}" if chg is not None else None
            st.metric("Prix", f"${price:,.2f}", delta=delta_str)

    # Badges row
    if badges:
        cols = st.columns(min(len(badges), 6))
        for i, (label, color) in enumerate(badges[:6]):
            with cols[i]:
                st.markdown(
                    f"<span style='background:#{'d4edda' if color=='green' else 'cce5ff' if color in ('blue','violet') else 'f8d7da' if color=='red' else 'fff3cd' if color=='orange' else 'e2e3e5'};padding:4px 10px;border-radius:12px;font-size:0.78rem;font-weight:600'>{label}</span>",
                    unsafe_allow_html=True,
                )
    st.write("")   # spacing


# ── Tab 1 : Price & Profile ───────────────────────────────────────────────────

def _tab_price_profile(ticker: str, info: dict) -> None:
    col_stats, col_chart = st.columns([1, 2.5])

    with col_stats:
        st.subheader("Données de marché")
        mcap = info.get("marketCap")
        ev   = info.get("enterpriseValue")

        _kv_table([
            ("Market Cap",        format_market_cap(mcap)),
            ("Enterprise Value",  format_market_cap(ev)),
            ("Volume moyen",      fmt_val(info.get("averageVolume"), "{:,.0f}")),
            ("52w High",          fmt_val(info.get("fiftyTwoWeekHigh"), "${:,.2f}")),
            ("52w Low",           fmt_val(info.get("fiftyTwoWeekLow"),  "${:,.2f}")),
            ("Float",             format_market_cap(info.get("floatShares") and
                                   (info["floatShares"] * (info.get("currentPrice") or 0)))),
        ])

        st.subheader("Business Summary")
        summary = info.get("longBusinessSummary") or "Non disponible."
        with st.expander("Lire le résumé"):
            st.write(summary)

    with col_chart:
        period_map = {"1 mois": "1mo", "6 mois": "6mo", "1 an": "1y", "5 ans": "5y"}
        period_lbl = st.segmented_control(
            "Période", list(period_map.keys()), default="1 an",
            label_visibility="collapsed",
        )
        period = period_map.get(period_lbl, "1y")
        hist = fetch_stock_history(ticker, period)
        if not hist.empty:
            st.plotly_chart(chart_price_history(hist, ticker), use_container_width=True)
        else:
            st.info("Historique de prix indisponible pour cette période.")


# ── Tab 2 : Valuation & Quality ───────────────────────────────────────────────

def _tab_valuation_quality(info: dict, quality: dict | None, piotroski: dict) -> None:
    col_val, col_qual = st.columns(2)

    with col_val:
        st.subheader("Ratios de Valorisation")
        _kv_table([
            ("P/E (trailing)",  fmt_val(info.get("trailingPE"),        "{:.1f}x")),
            ("P/E (forward)",   fmt_val(info.get("forwardPE"),         "{:.1f}x")),
            ("P/B",             fmt_val(info.get("priceToBook"),       "{:.2f}x")),
            ("PEG Ratio",       fmt_val(info.get("pegRatio"),          "{:.2f}x")),
            ("EV/EBITDA",       fmt_val(info.get("enterpriseToEbitda"),"{:.1f}x")),
            ("EV/Revenue",      fmt_val(info.get("enterpriseToRevenue"),"{:.1f}x")),
            ("FCF Yield",       _fcf_yield(info)),
        ])

        st.subheader("Marges")
        _kv_table([
            ("Marge brute",      fmt_pct(info.get("grossMargins"))),
            ("Marge opérationnelle", fmt_pct(info.get("operatingMargins"))),
            ("Marge nette",      fmt_pct(info.get("profitMargins"))),
            ("ROE",              fmt_pct(info.get("returnOnEquity"))),
            ("ROA",              fmt_pct(info.get("returnOnAssets"))),
            ("Croissance Rev.",  fmt_pct(info.get("revenueGrowth"), signed=True)),
            ("Croissance EPS",   fmt_pct(info.get("earningsGrowth"), signed=True)),
        ])

    with col_qual:
        # Quality Rating
        st.subheader("Quality Rating")
        if quality:
            score = quality["score"]
            color = quality["color"]
            st.markdown(
                f"<div style='text-align:center'>"
                f"<span style='font-size:3rem;font-weight:700;color:{color}'>{score}</span>"
                f"<span style='font-size:1.2rem;color:{color}'>/100</span>"
                f"<br><b style='color:{color}'>{quality['label']}</b></div>",
                unsafe_allow_html=True,
            )
            st.progress(score / 100)
            st.caption(
                "Score calculé à partir des marges, ROE, levier, FCF yield et croissance des revenus."
            )
        else:
            st.info("Données insuffisantes pour calculer un Quality Rating.")

        st.divider()

        # Piotroski F-Score
        st.subheader("Piotroski F-Score")
        if piotroski["available"]:
            score = piotroski["score"]
            if score >= 7:   label, color = f"{score}/9  ✅ Fort",   "green"
            elif score >= 4: label, color = f"{score}/9  ⚖️ Neutre", "orange"
            else:            label, color = f"{score}/9  ⚠️ Faible", "red"

            st.markdown(
                f"<h2 style='text-align:center;color:{color}'>{label}</h2>",
                unsafe_allow_html=True,
            )
            st.progress(score / 9)
            with st.expander("Détail des 9 critères"):
                for criterion, val in piotroski["details"].items():
                    icon = "✅" if val else "❌"
                    st.markdown(f"{icon} {criterion}")
        else:
            st.info(
                "Données financières insuffisantes pour calculer le score Piotroski. "
                "Vérifiez que le ticker dispose d'au moins 2 ans d'états financiers annuels."
            )


# ── Tab 3 : Financials ────────────────────────────────────────────────────────

def _tab_financials(stmts: dict) -> None:
    fin      = stmts["financials"]
    earnings = stmts["earnings"]

    col_l, col_r = st.columns(2)
    fig_rev, fig_ni = chart_revenue_net_income(fin)

    with col_l:
        st.subheader("Revenue Annuel")
        if not fin.empty and "Total Revenue" in fin.index:
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.info("Données de revenu non disponibles.")

    with col_r:
        st.subheader("Net Income Annuel")
        if not fin.empty and "Net Income" in fin.index:
            st.plotly_chart(fig_ni, use_container_width=True)
        else:
            st.info("Données de Net Income non disponibles.")

    st.subheader("EPS Trimestriel")
    fig_eps = chart_eps(earnings)
    if fig_eps.data:
        st.plotly_chart(fig_eps, use_container_width=True)
    else:
        st.info("EPS trimestriel non disponible via l'API pour ce ticker.")


# ── Tab 4 : Balance Sheet & Analysts ─────────────────────────────────────────

def _tab_balance_analysts(info: dict) -> None:
    col_bs, col_an = st.columns(2)

    with col_bs:
        st.subheader("Bilan & Structure Financière")
        total_debt = info.get("totalDebt")
        total_cash = info.get("totalCash")
        de_raw     = info.get("debtToEquity")
        de         = (de_raw / 100) if (de_raw is not None and de_raw > 10) else de_raw

        _kv_table([
            ("Dette totale",   format_market_cap(total_debt)),
            ("Cash & équiv.",  format_market_cap(total_cash)),
            ("Dette nette",    format_market_cap(
                (total_debt - total_cash) if (total_debt and total_cash) else None
            )),
            ("Debt / Equity",  fmt_val(de, "{:.2f}x")),
            ("Current Ratio",  fmt_val(info.get("currentRatio"), "{:.2f}")),
            ("Quick Ratio",    fmt_val(info.get("quickRatio"),   "{:.2f}")),
        ])

        st.subheader("Dividende")
        _kv_table([
            ("Dividend Yield", _div_yield(info)),
            ("Payout Ratio",   fmt_pct(info.get("payoutRatio"))),
            ("Dividende/action", fmt_val(info.get("dividendRate"), "${:.2f}")),
            ("Ex-Date",        str(info.get("exDividendDate", "N/A"))),
        ])

    with col_an:
        st.subheader("Recommandations Analystes")
        target     = info.get("targetMeanPrice")
        target_low = info.get("targetLowPrice")
        target_hi  = info.get("targetHighPrice")
        rec        = info.get("recommendationKey", "").replace("_", " ").title()
        price      = info.get("currentPrice") or info.get("regularMarketPreviousClose")
        n_analysts = info.get("numberOfAnalystOpinions")

        if target and price:
            upside = (target / price - 1)
            col1, col2 = st.columns(2)
            col1.metric("Target consensus", f"${target:,.2f}",
                        f"{upside:+.1%} vs prix actuel")
            if n_analysts:
                col2.metric("Nb. analystes", str(n_analysts))

            if target_low and target_hi:
                st.caption(f"Fourchette : ${target_low:,.2f} — ${target_hi:,.2f}")
        else:
            st.info("Pas de target de prix disponible pour ce ticker.")

        if rec:
            rec_color = {"Buy": "green", "Strong Buy": "green", "Hold": "orange",
                         "Sell": "red", "Underperform": "red"}.get(rec, "gray")
            st.markdown(
                f"<div style='margin-top:12px;text-align:center;"
                f"background:#{'d4edda' if rec_color=='green' else 'f8d7da' if rec_color=='red' else 'fff3cd'};"
                f"border-radius:8px;padding:10px'>"
                f"<b style='font-size:1.1rem'>Consensus : {rec}</b></div>",
                unsafe_allow_html=True,
            )

        st.divider()
        st.subheader("Beta & Volatilité")
        _kv_table([
            ("Beta",                  fmt_val(info.get("beta"), "{:.2f}")),
            ("52w Volatilité impl.",  "N/A"),
            ("Short % of Float",      fmt_pct(info.get("shortPercentOfFloat"))),
        ])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _kv_table(rows: list[tuple]) -> None:
    """Render a clean key-value table using st.markdown."""
    lines = []
    for key, val in rows:
        color = "inherit"
        if val == "N/A":
            color = "#9e9e9e"
        lines.append(
            f"<tr><td style='padding:4px 8px;color:#555;font-size:0.85rem'>{key}</td>"
            f"<td style='padding:4px 8px;font-weight:600;color:{color}'>{val}</td></tr>"
        )
    st.markdown(
        f"<table style='width:100%;border-collapse:collapse'>{''.join(lines)}</table>",
        unsafe_allow_html=True,
    )
    st.write("")  # spacing


def _div_yield(info: dict) -> str:
    """Compute dividend yield from dividendRate / price.
    Bypasses yfinance's inconsistent dividendYield field (returns decimal OR already-pct
    depending on the ticker). dividendRate and currentPrice are always in the same currency."""
    rate  = info.get("dividendRate")
    price = info.get("currentPrice") or info.get("regularMarketPreviousClose")
    if rate and price and float(price) > 0:
        return fmt_pct(float(rate) / float(price), decimals=2)
    return "N/A"


def _fcf_yield(info: dict) -> str:
    fcf  = info.get("freeCashflow")
    mcap = info.get("marketCap")
    if fcf is None or not mcap or mcap <= 0:
        return "N/A"
    return fmt_pct(fcf / mcap)
