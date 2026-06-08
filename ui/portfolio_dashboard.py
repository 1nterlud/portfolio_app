"""
Portfolio Dashboard page — full analysis pipeline + tab rendering.
Called by app.py when the user selects "Portfolio Dashboard".
"""
import streamlit as st

from data.market_data import fetch_prices
from data.fundamentals import fetch_fundamentals
from analytics.metrics import calc_metrics
from analytics.mpt import calc_mpt
from analytics.allocation import build_sector_comparison
from ui.kpis import render_kpis
from ui.tabs import (
    render_tab_allocation,
    render_tab_risk,
    render_tab_performance,
    render_tab_optimization,
    render_tab_details,
)
from ui.diagnosis import render_diagnosis
from utils.validation import validate_tickers


def render_portfolio_dashboard(inputs: dict) -> None:
    """Run the full portfolio pipeline and render all tabs."""

    # ── Ticker validation (optional standalone action) ────────────────────────
    if inputs.get("validate_btn"):
        raw = inputs.get("df_port_raw")
        if raw is None or raw.empty:
            st.warning("Aucune position à vérifier. Entrez vos positions d'abord.")
        else:
            with st.spinner("Vérification des tickers..."):
                results = validate_tickers(tuple(sorted(raw["Symbol"].tolist())))
            ok  = [t for t, v in results.items() if v]
            bad = [t for t, v in results.items() if not v]
            if ok:  st.success(f"✅ Tickers valides : {', '.join(ok)}")
            if bad: st.error(f"❌ Tickers introuvables : {', '.join(bad)}")
        if not inputs.get("run_btn"):
            st.stop()

    if not inputs.get("run_btn"):
        st.info(
            "Configurez vos positions dans le panneau gauche, "
            "puis cliquez sur **🚀 Lancer l'analyse**."
        )
        return

    df_port_raw = inputs.get("df_port_raw")
    if df_port_raw is None or df_port_raw.empty:
        st.error("Aucune position valide. Vérifiez le format de saisie (`TICKER, Quantité`).")
        return

    try:
        tickers   = df_port_raw["Symbol"].tolist()
        benchmark = inputs["benchmark"]
        risk_free = inputs["risk_free"]

        # 1. Prices
        with st.spinner("Chargement des prix historiques..."):
            all_tickers = tuple(sorted(set(tickers + [benchmark])))
            prices = fetch_prices(all_tickers, inputs["start_date"], inputs["end_date"])
            prices = prices.ffill().dropna(how="all")

        # 2. Validate tickers
        valid   = [t for t in tickers if t in prices.columns]
        missing = [t for t in tickers if t not in prices.columns]
        if missing:
            st.warning(f"Tickers ignorés (données indisponibles) : {', '.join(missing)}")
        if not valid:
            st.error("Aucun ticker valide. Vérifiez vos positions.")
            return

        # 3. Weights
        df_port = df_port_raw[df_port_raw["Symbol"].isin(valid)].copy()
        last_prices = prices[valid].iloc[-1]
        df_port["Val"] = df_port["Qty"] * df_port["Symbol"].map(last_prices)
        total_val      = df_port["Val"].sum()
        df_port["W"]   = df_port["Val"] / total_val

        # 4. Returns
        rets    = prices.pct_change().dropna()
        weights = df_port.set_index("Symbol")["W"].reindex(valid).values
        port_rets = rets[valid].dot(weights)

        # 5. Benchmark — explicit warning if not found
        bench_cum = None
        mpt       = None
        if benchmark in rets.columns:
            bench_rets = rets[benchmark]
            bench_cum  = (1 + bench_rets).cumprod()
            mpt        = calc_mpt(port_rets, bench_rets)
        else:
            st.warning(
                f"⚠️ Benchmark **{benchmark}** introuvable dans les données téléchargées. "
                "Les statistiques MPT (Alpha, Bêta, R) ne seront pas affichées."
            )

        # 6. Metrics
        m = calc_metrics(port_rets, risk_free)

        # 7. Fundamentals
        with st.spinner("Récupération des fondamentaux..."):
            funds = fetch_fundamentals(tuple(sorted(valid)))

        merged  = df_port.merge(funds, on="Symbol", how="left")
        comp_df = build_sector_comparison(merged)

        # ── KPIs ──────────────────────────────────────────────────────────────
        render_kpis(m, total_val)
        st.divider()

        # ── Tabs ──────────────────────────────────────────────────────────────
        tabs = st.tabs([
            "📊 Allocation & Secteurs",
            "⚠️ Risque & Simulation",
            "🚀 Performance & MPT",
            "🔗 Corrélations & Optimisation",
            "📋 Positions & Export",
            "🏥 Diagnostic",
        ])

        with tabs[0]: render_tab_allocation(df_port, comp_df)
        with tabs[1]: render_tab_risk(m, port_rets, total_val)
        with tabs[2]: render_tab_performance(m, mpt, bench_cum, benchmark,
                                              port_rets, rets, df_port)
        with tabs[3]: render_tab_optimization(rets, df_port, risk_free, m)
        with tabs[4]: render_tab_details(merged, m, mpt or {}, benchmark)
        with tabs[5]: render_diagnosis(m, mpt or {}, df_port, comp_df, benchmark)

    except Exception as exc:
        st.error(f"Erreur inattendue : {exc}")
        with st.expander("Détails techniques"):
            st.exception(exc)
