"""
Portfolio Dashboard page — full analysis pipeline + tab rendering.
Called by app.py when the user selects "Portfolio Dashboard".
"""
import streamlit as st
from datetime import datetime

from data.market_data import fetch_prices
from data.fundamentals import fetch_fundamentals
from analytics.metrics import calc_metrics
from analytics.mpt import calc_mpt
from analytics.allocation import build_sector_comparison, calc_diversification_score
from analytics.health_score import calc_health_score
from analytics.optimization import max_sharpe_portfolio
from ui.kpis import render_hero, render_kpis
from ui.tabs import (
    render_tab_allocation,
    render_tab_risk,
    render_tab_performance,
    render_tab_optimization,
    render_tab_rolling_stress,
    render_tab_backtest,
    render_tab_details,
)
from ui.diagnosis import render_diagnosis, build_proactive_alerts
from ui.macro_tab import render_tab_macro
from utils.validation import validate_tickers
from utils.formatting import natural_summary
from utils.components import (
    render_alert_banner, render_freshness_footer,
    render_page_hero, render_empty_state,
)
from config import __version__


def render_portfolio_dashboard(inputs: dict) -> None:
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
        render_page_hero(
            eyebrow="Tableau de bord",
            title="Portfolio Dashboard",
            subtitle="Analyse complète de votre allocation, performance, risque et optimisation.",
            pills=[
                ("📊", "Allocation & secteurs"),
                ("⚠️", "Risque & Monte Carlo"),
                ("🚀", "MPT & Optimisation"),
                ("🏥", "Diagnostic Santé"),
            ],
        )
        render_empty_state(
            "Prêt à analyser votre portefeuille",
            "Configurez vos positions dans le panneau gauche, puis cliquez sur "
            "🚀 Lancer l'analyse. Format : TICKER, Quantité  ou  TICKER, Quantité, Prix d'achat.",
            "📊",
        )
        return

    df_port_raw = inputs.get("df_port_raw")
    if df_port_raw is None or df_port_raw.empty:
        st.error("Aucune position valide. Vérifiez le format de saisie "
                 "(`TICKER, Quantité` ou `TICKER, Quantité, Prix d'achat`).")
        return

    try:
        tickers   = df_port_raw["Symbol"].tolist()
        benchmark = inputs["benchmark"]
        risk_free = inputs["risk_free"]

        # 1. Prices
        with st.spinner("Chargement des prix historiques..."):
            all_tickers = tuple(sorted(set(tickers + [benchmark])))
            prices = fetch_prices(all_tickers, inputs["start_date"], inputs["end_date"])
        if prices.empty:
            st.error(
                "Impossible de récupérer les prix. Causes possibles : tickers invalides, "
                "période sans données, ou indisponibilité temporaire de Yahoo Finance. "
                "Vérifiez vos positions puis réessayez avec 🔄 Rafraîchir les données."
            )
            return
        prices = prices.ffill().dropna(how="all")
        fetched_at = datetime.now()

        # 2. Validate
        valid   = [t for t in tickers if t in prices.columns]
        missing = [t for t in tickers if t not in prices.columns]
        if missing:
            st.warning(f"Tickers ignorés (données indisponibles) : {', '.join(missing)}")
        if not valid:
            st.error("Aucun ticker valide. Vérifiez vos positions.")
            return

        # 3. Weights & values
        df_port = df_port_raw[df_port_raw["Symbol"].isin(valid)].copy()
        last_prices = prices[valid].iloc[-1]
        df_port["Prix"] = df_port["Symbol"].map(last_prices)
        df_port["Val"]  = df_port["Qty"] * df_port["Prix"]
        total_val       = df_port["Val"].sum()
        df_port["W"]    = df_port["Val"] / total_val

        # 4. Returns
        rets    = prices.pct_change().dropna()
        weights = df_port.set_index("Symbol")["W"].reindex(valid).values
        port_rets = rets[valid].dot(weights)

        # 5. Benchmark
        bench_cum  = None
        bench_rets = None
        mpt        = None
        if benchmark in rets.columns:
            bench_rets = rets[benchmark]
            bench_cum  = (1 + bench_rets).cumprod()
            mpt        = calc_mpt(port_rets, bench_rets)
        else:
            st.warning(
                f"⚠️ Benchmark **{benchmark}** introuvable dans les données. "
                "Les statistiques MPT ne seront pas affichées."
            )

        # 6. Metrics
        m = calc_metrics(port_rets, risk_free)

        # 7. Fundamentals
        with st.spinner("Récupération des fondamentaux..."):
            funds = fetch_fundamentals(tuple(sorted(valid)))

        merged  = df_port.merge(funds, on="Symbol", how="left",
                                suffixes=("", "_f"))
        # Avoid duplicate price column (we already have one from market_data)
        if "Prix_f" in merged.columns:
            merged = merged.drop(columns=["Prix_f"])
        comp_df = build_sector_comparison(merged)

        # 8. Health + alerts banner
        sector_w   = (comp_df.set_index("Secteur")["Portefeuille"]
                      if "Portefeuille" in comp_df.columns else None)
        div_score  = calc_diversification_score(
            df_port.set_index("Symbol")["W"],
            sector_w if sector_w is not None else df_port.set_index("Symbol")["W"] * 0,
        )
        health    = calc_health_score(m, mpt, div_score)

        # ── Page header ───────────────────────────────────────────────────────
        n_positions = len(df_port)
        period_days = (inputs["end_date"] - inputs["start_date"]).days
        render_page_hero(
            eyebrow=f"Portefeuille · {benchmark}",
            title="Tableau de bord en direct",
            subtitle="Analyse en temps réel de votre allocation, performance et niveau de risque.",
            pills=[
                ("💼", f"{n_positions} position{'s' if n_positions > 1 else ''}"),
                ("🎯", f"Benchmark : {benchmark}"),
                ("📅", f"Période : ~{period_days // 365} an{'s' if period_days // 365 > 1 else ''}"),
                ("💵", f"Taux sans risque : {risk_free * 100:.1f}%"),
            ],
        )

        # Top alerts banner (visible across the dashboard)
        render_alert_banner(build_proactive_alerts(m, mpt, df_port, comp_df))

        # ── Hero ──────────────────────────────────────────────────────────────
        render_hero(total_val, m, health, fetched_at, n_days=len(port_rets))
        render_kpis(m, mpt)

        # ── Résumé exécutif ───────────────────────────────────────────────────
        with st.expander("📝  Résumé exécutif", expanded=True):
            st.markdown(natural_summary(m, mpt, benchmark, div_score, health))

        st.divider()

        # ── Tabs ──────────────────────────────────────────────────────────────
        tabs = st.tabs([
            "📊 Allocation & Secteurs",
            "⚠️ Risque & Simulation",
            "🚀 Performance & MPT",
            "🔗 Corrélations & Optim.",
            "📈 Rolling & Stress",
            "🔁 Backtest cible",
            "📋 Positions & Export",
            "🌍 Macro",
            "🏥 Diagnostic",
        ])

        def _safe_tab(fn, *args, label="ce tab", **kwargs):
            try:
                fn(*args, **kwargs)
            except Exception as _e:
                st.error(f"Erreur dans {label} : {_e}")
                with st.expander("Détails techniques"):
                    st.exception(_e)

        with tabs[0]:
            _safe_tab(render_tab_allocation, df_port, comp_df, label="Allocation")
        with tabs[1]:
            _safe_tab(render_tab_risk, m, port_rets, total_val, label="Risque",
                      mc_distribution=inputs.get("mc_distribution", "normal"),
                      mc_t_df=inputs.get("mc_t_df", 5))
        with tabs[2]:
            _safe_tab(render_tab_performance, m, mpt, bench_cum, benchmark,
                      port_rets, rets, df_port, label="Performance")
        with tabs[3]:
            _safe_tab(render_tab_optimization, rets, df_port, risk_free, m,
                      label="Optimisation",
                      max_weight=inputs.get("max_weight", 1.0),
                      min_weight=inputs.get("min_weight", 0.0),
                      last_prices=last_prices, total_val=total_val)
        with tabs[4]:
            _safe_tab(render_tab_rolling_stress, port_rets, risk_free,
                      label="Rolling & Stress",
                      weights=df_port.set_index("Symbol")["W"].to_dict())
        with tabs[5]:
            valid_for_opt = [c for c in df_port["Symbol"].tolist() if c in rets.columns]
            target_w = {}
            if len(valid_for_opt) >= 2:
                res = max_sharpe_portfolio(
                    rets[valid_for_opt], risk_free=risk_free,
                    max_weight=inputs.get("max_weight", 1.0),
                    min_weight=inputs.get("min_weight", 0.0),
                )
                if res:
                    target_w = res["weights"]
            current_w = df_port.set_index("Symbol")["W"].to_dict()
            _safe_tab(render_tab_backtest, rets[valid_for_opt], current_w, target_w,
                      bench_rets, benchmark, label="Backtest")
        with tabs[6]:
            _safe_tab(render_tab_details, merged, m, mpt or {}, benchmark,
                      label="Positions")
        with tabs[7]:
            _safe_tab(render_tab_macro, label="Macro")
        with tabs[8]:
            _safe_tab(render_diagnosis, m, mpt or {}, df_port, comp_df, benchmark,
                      label="Diagnostic",
                      portfolio_name="Mon Portefeuille",
                      total_val=total_val,
                      fetched_at=fetched_at)

        render_freshness_footer(__version__, fetched_at)

    except Exception as exc:
        st.error(f"Erreur inattendue : {exc}")
        with st.expander("Détails techniques"):
            st.exception(exc)
