"""
Stock Research page — complete single-ticker fundamental analysis with news,
insiders, DCF and earnings calendar.
"""
import streamlit as st
import pandas as pd

from data.single_stock import (
    fetch_stock_info, fetch_stock_history, fetch_stock_financials,
    fetch_stock_news, fetch_insider_transactions,
    fetch_institutional_holders, fetch_earnings_calendar,
)
from data.normalize import normalize_stock_info
from analytics.single_stock_metrics import calc_piotroski, calc_quality_rating, get_stock_badges
from analytics.dcf import two_stage_dcf
from ui.charts import chart_price_history, chart_revenue_net_income, chart_eps
from utils.formatting import format_market_cap, fmt_val, fmt_pct
from utils.components import (
    render_badges, render_empty_state, render_kv_table,
    render_page_hero, render_section_title, render_hero_value,
)


# ── Entry point ───────────────────────────────────────────────────────────────

def render_stock_research(ticker: str = "AAPL", analyze: bool = False) -> None:
    if not analyze:
        render_page_hero(
            eyebrow="Recherche action",
            title="Stock Research",
            subtitle="Analyse fondamentale complète : valorisation, qualité, DCF, news et insiders.",
            pills=[("📈", "Prix & profil"), ("📊", "Valorisation"),
                   ("💰", "Financials"), ("🧮", "DCF Simulator")],
        )
        render_empty_state(
            "Aucun ticker analysé",
            "Entrez un ticker dans le panneau gauche puis cliquez sur Analyser →.",
            "🔍",
        )
        return
    if not ticker:
        st.warning("Veuillez entrer un ticker valide.")
        return

    with st.spinner(f"Analyse de **{ticker}** en cours..."):
        info_raw  = fetch_stock_info(ticker)
        stmts     = fetch_stock_financials(ticker)

    if not info_raw:
        render_empty_state(
            f"Ticker **{ticker}** introuvable",
            "Vérifiez l'orthographe (ex: AAPL, MSFT, ASML.AS). "
            "Pour les marchés européens : suffixe `.PA`, `.AS`, `.DE`.",
            "🔍",
        )
        return

    snap = normalize_stock_info(ticker, info_raw)

    quality   = calc_quality_rating(info_raw)
    piotroski = calc_piotroski(stmts["financials"], stmts["balance_sheet"], stmts["cashflow"])
    p_score   = piotroski["score"] if piotroski["available"] else None
    badges    = get_stock_badges(info_raw, quality, p_score)

    _render_header(ticker, snap, badges)
    st.divider()

    tabs = st.tabs([
        "📈 Prix & Profil",
        "📊 Valorisation & Qualité",
        "💰 Résultats Financiers",
        "🏦 Bilan & Analystes",
        "📰 News & Insiders",
        "🧮 DCF Simulator",
    ])
    with tabs[0]: _tab_price_profile(ticker, snap)
    with tabs[1]: _tab_valuation_quality(snap, quality, piotroski)
    with tabs[2]: _tab_financials(stmts)
    with tabs[3]: _tab_balance_analysts(snap)
    with tabs[4]: _tab_news_insiders(ticker)
    with tabs[5]: _tab_dcf(snap, stmts)


# ── Header ─────────────────────────────────────────────────────────────────────

def _render_header(ticker: str, snap, badges: list) -> None:
    # Premium page hero with company name + meta pills
    pills = []
    if snap.sector:    pills.append(("🏢", snap.sector))
    if snap.industry:  pills.append(("⚙️", snap.industry))
    if snap.exchange:  pills.append(("🌐", snap.exchange))
    if snap.market_cap: pills.append(("💵", format_market_cap(snap.market_cap)))

    render_page_hero(
        eyebrow=f"Stock Research · {ticker}",
        title=snap.name or ticker,
        subtitle="Analyse fondamentale, valorisation et qualité.",
        pills=pills,
    )

    col_price, col_badges = st.columns([1, 2])
    with col_price:
        if snap.price:
            render_hero_value(
                f"Prix {ticker}",
                f"${snap.price:,.2f}",
                f"Target : ${snap.target_mean:,.2f}" if snap.target_mean else None,
                "success" if (snap.target_mean and snap.target_mean > snap.price) else "neutral",
            )
    with col_badges:
        st.markdown("##### Badges qualité")
        render_badges(badges)


# ── Tab 1 : Price & Profile ───────────────────────────────────────────────────

def _tab_price_profile(ticker: str, snap) -> None:
    col_stats, col_chart = st.columns([1, 2.5])

    with col_stats:
        render_section_title("🏷️", "Données de marché", "Cap & valorisation")
        render_kv_table([
            ("Market Cap",       format_market_cap(snap.market_cap)),
            ("Enterprise Value", format_market_cap(snap.enterprise_value)),
            ("52w High",         fmt_val(snap.target_high, "${:,.2f}")),
            ("52w Low",          fmt_val(snap.target_low,  "${:,.2f}")),
        ])

        render_section_title("📖", "Business Summary", "Description de l'activité")
        if snap.summary:
            with st.expander("Lire le résumé"):
                st.write(snap.summary)
        else:
            st.caption("_Résumé non disponible._")

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
            render_empty_state("Historique indisponible",
                              "Cette période n'a pas pu être chargée.", "📉")


# ── Tab 2 : Valuation & Quality ───────────────────────────────────────────────

def _tab_valuation_quality(snap, quality, piotroski) -> None:
    col_val, col_qual = st.columns(2)

    with col_val:
        render_section_title("📐", "Valorisation", "Multiples & ratios")
        render_kv_table([
            ("P/E (trailing)",  fmt_val(snap.pe_trailing,  "{:.1f}x")),
            ("P/E (forward)",   fmt_val(snap.pe_forward,   "{:.1f}x")),
            ("P/B",             fmt_val(snap.price_book,   "{:.2f}x")),
            ("PEG Ratio",       fmt_val(snap.peg,          "{:.2f}x")),
            ("EV/EBITDA",       fmt_val(snap.ev_ebitda,    "{:.1f}x")),
            ("EV/Revenue",      fmt_val(snap.ev_revenue,   "{:.1f}x")),
            ("FCF Yield",       fmt_pct(snap.fcf_yield)),
        ])

        render_section_title("💹", "Marges & Rentabilité", "")
        render_kv_table([
            ("Marge brute",       fmt_pct(snap.gross_margin)),
            ("Marge opérationnelle", fmt_pct(snap.operating_margin)),
            ("Marge nette",       fmt_pct(snap.profit_margin)),
            ("ROE",               fmt_pct(snap.roe)),
            ("ROA",               fmt_pct(snap.roa)),
            ("Croissance Rev.",   fmt_pct(snap.revenue_growth, signed=True)),
            ("Croissance EPS",    fmt_pct(snap.earnings_growth, signed=True)),
        ])

    with col_qual:
        render_section_title("⭐", "Quality Rating", "Score qualité fondamentale")
        if quality:
            score, color = quality["score"], quality["color"]
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
            render_empty_state("Quality Rating indisponible",
                              "Pas assez de données fondamentales.", "📊")

        st.divider()

        render_section_title("🏅", "Piotroski F-Score", "9 critères fondamentaux")
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
            render_empty_state(
                "Piotroski indisponible",
                "Le ticker doit avoir au moins 2 ans d'états financiers annuels.",
                "📒",
            )


# ── Tab 3 : Financials ────────────────────────────────────────────────────────

def _tab_financials(stmts: dict) -> None:
    fin      = stmts["financials"]
    earnings = stmts["earnings"]

    col_l, col_r = st.columns(2)
    fig_rev, fig_ni = chart_revenue_net_income(fin)

    with col_l:
        render_section_title("💰", "Revenue annuel", "Sur les derniers exercices")
        if not fin.empty and "Total Revenue" in fin.index:
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            render_empty_state("Revenue indisponible",
                              "Pas de données de revenue annuel.", "💰")

    with col_r:
        render_section_title("📈", "Net income annuel", "")
        if not fin.empty and "Net Income" in fin.index:
            st.plotly_chart(fig_ni, use_container_width=True)
        else:
            render_empty_state("Net Income indisponible",
                              "Pas de données de net income annuel.", "📉")

    render_section_title("🧾", "EPS trimestriel", "10 derniers trimestres")
    fig_eps = chart_eps(earnings)
    if fig_eps.data:
        st.plotly_chart(fig_eps, use_container_width=True)
    else:
        render_empty_state("EPS Trimestriel indisponible",
                          "L'API n'expose pas l'EPS pour ce ticker.", "📊")


# ── Tab 4 : Balance Sheet & Analysts ─────────────────────────────────────────

def _tab_balance_analysts(snap) -> None:
    col_bs, col_an = st.columns(2)

    with col_bs:
        render_section_title("🏦", "Bilan & Structure", "Dette, cash, liquidité")
        net_debt = ((snap.total_debt - snap.total_cash)
                    if (snap.total_debt and snap.total_cash) else None)
        render_kv_table([
            ("Dette totale",  format_market_cap(snap.total_debt)),
            ("Cash & équiv.", format_market_cap(snap.total_cash)),
            ("Dette nette",   format_market_cap(net_debt)),
            ("Debt / Equity", fmt_val(snap.debt_to_equity, "{:.2f}x")),
            ("Current Ratio", fmt_val(snap.current_ratio, "{:.2f}")),
            ("Quick Ratio",   fmt_val(snap.quick_ratio,   "{:.2f}")),
        ])

        render_section_title("💵", "Dividende", "Yield, payout, ex-date")
        render_kv_table([
            ("Dividend Yield",   fmt_pct(snap.div_yield, decimals=2)),
            ("Payout Ratio",     fmt_pct(snap.payout_ratio)),
            ("Dividende/action", fmt_val(snap.div_rate, "${:.2f}")),
            ("Ex-Date",          str(snap.ex_div_date or "N/A")),
        ])

    with col_an:
        render_section_title("🎯", "Analystes", "Recommandations & targets")
        target = snap.target_mean
        price  = snap.price
        if target and price:
            upside = (target / price - 1)
            col1, col2 = st.columns(2)
            col1.metric("Target consensus", f"${target:,.2f}",
                        f"{upside:+.1%} vs prix actuel")
            if snap.n_analysts:
                col2.metric("Nb. analystes", str(snap.n_analysts))
            if snap.target_low and snap.target_high:
                st.caption(f"Fourchette : ${snap.target_low:,.2f} — ${snap.target_high:,.2f}")
        else:
            render_empty_state("Pas de target analyste",
                              "Fréquent pour les small caps.", "🎯")

        if snap.recommendation:
            rec = snap.recommendation
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
        render_section_title("📊", "Beta & volatilité", "Sensibilité au marché")
        render_kv_table([
            ("Beta",             fmt_val(snap.beta, "{:.2f}")),
            ("Short % of Float", fmt_pct(snap.short_pct_float)),
        ])


# ── Tab 5 : News & Insiders ──────────────────────────────────────────────────

def _tab_news_insiders(ticker: str) -> None:
    col_news, col_ins = st.columns([1.4, 1])

    with col_news:
        render_section_title("📰", "News récentes", "6 derniers articles")
        news = fetch_stock_news(ticker, limit=6)
        if not news:
            render_empty_state("Aucune news disponible",
                              "L'API n'expose pas de news pour ce ticker.", "📰")
        else:
            for item in news:
                st.markdown(
                    f"**[{item['title']}]({item['link']})**  \n"
                    f"<span style='color:#64748b;font-size:0.8rem'>"
                    f"{item['publisher']} · {item['date']}</span>",
                    unsafe_allow_html=True,
                )
                st.divider()

        render_section_title("📅", "Prochaines dates", "Calendrier earnings")
        cal = fetch_earnings_calendar(ticker)
        if cal and isinstance(cal, dict) and cal:
            rows = []
            for k, v in cal.items():
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        rows.append((f"{k} — {kk}", str(vv)))
                else:
                    rows.append((k, str(v)))
            render_kv_table(rows[:8])
        else:
            st.caption("_Pas de calendrier disponible._")

    with col_ins:
        render_section_title("👤", "Transactions insiders", "Récentes")
        ins = fetch_insider_transactions(ticker)
        if ins.empty:
            render_empty_state("Pas de transactions",
                              "Aucune transaction d'initié n'est exposée par l'API.",
                              "👤")
        else:
            keep = [c for c in ["Insider", "Position", "Transaction", "Value", "Start Date"]
                    if c in ins.columns]
            st.dataframe(ins[keep] if keep else ins, use_container_width=True, hide_index=True)

        render_section_title("🏛️", "Top institutionnels", "Actionnariat")
        inst = fetch_institutional_holders(ticker)
        if inst.empty:
            render_empty_state("Pas d'institutionnels",
                              "Aucune donnée d'actionnariat institutionnel.", "🏦")
        else:
            keep = [c for c in ["Holder", "Shares", "Date Reported",
                                "% Out", "Value"] if c in inst.columns]
            st.dataframe(inst[keep] if keep else inst, use_container_width=True, hide_index=True)


# ── Tab 6 : DCF simulator ────────────────────────────────────────────────────

def _tab_dcf(snap, stmts: dict) -> None:
    render_section_title("🧮", "DCF Simulator",
                         "Discounted Cash Flow · what-if")
    st.caption(
        "Outil pédagogique : entrez vos hypothèses et obtenez la juste valeur "
        "implicite par action."
    )

    # Default FCF from cashflow statement if available
    cf = stmts.get("cashflow", pd.DataFrame())
    fcf_default = None
    if not cf.empty and "Free Cash Flow" in cf.index:
        try:
            fcf_default = float(cf.loc["Free Cash Flow"].iloc[0])
        except Exception:
            pass
    if fcf_default is None and snap.market_cap and snap.fcf_yield:
        fcf_default = snap.market_cap * snap.fcf_yield

    if fcf_default is None or fcf_default <= 0:
        render_empty_state("FCF base introuvable",
                          "Pas assez de données pour pré-remplir le DCF.", "🧮")
        fcf_default = 1e9

    col_l, col_r = st.columns(2)
    with col_l:
        fcf_base = st.number_input("FCF actuel (USD)", value=float(fcf_default), step=1e8,
                                   format="%.0f")
        growth_high = st.slider("Croissance années 1-5 (%)", -5.0, 25.0, 8.0, step=0.5) / 100
        growth_term = st.slider("Croissance terminale (%)", 0.0, 5.0, 2.5, step=0.1) / 100
        wacc        = st.slider("WACC (%)", 5.0, 15.0, 9.0, step=0.5) / 100

    info_shares = None
    info_debt   = (snap.total_debt or 0) - (snap.total_cash or 0)

    with col_r:
        st.markdown("**Données du ticker**")
        render_kv_table([
            ("Prix actuel",    f"${snap.price:,.2f}" if snap.price else "N/A"),
            ("Market Cap",     format_market_cap(snap.market_cap)),
            ("Dette nette",    format_market_cap(info_debt)),
        ])
        shares_default = (snap.market_cap / snap.price) if (snap.market_cap and snap.price) else 1
        shares = st.number_input("Shares outstanding (en millions)",
                                 value=float(shares_default / 1e6),
                                 step=10.0) * 1e6

    res = two_stage_dcf(fcf_base, growth_high, growth_term, wacc,
                        shares_out=shares, net_debt=info_debt)
    if "error" in res:
        st.error(res["error"])
        return

    fair = res["per_share"]
    cur  = snap.price or 0
    delta_pct = (fair / cur - 1) if cur > 0 else None

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Juste valeur / action", f"${fair:,.2f}")
    if delta_pct is not None:
        c2.metric("Prix actuel", f"${cur:,.2f}",
                  f"{delta_pct:+.1%} de marge")
    c3.metric("Valeur d'entreprise", format_market_cap(res["enterprise"]))
    st.caption(
        f"NPV période explicite : {format_market_cap(res['npv_explicit'])}  ·  "
        f"NPV terminale : {format_market_cap(res['npv_terminal'])}"
    )
    st.warning("⚠️ Estimation pédagogique sensible aux hypothèses. Pas un conseil d'investissement.")
