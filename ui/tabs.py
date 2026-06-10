"""
One render_tab_* function per portfolio tab.
Each receives only the data it needs — no global state.
"""
import streamlit as st
import pandas as pd
import numpy as np

from config import METRIC_EXPLANATIONS
from analytics.monte_carlo import monte_carlo
from analytics.allocation import top_contributors
from analytics.optimization import (
    calc_random_cloud as _calc_random_cloud,
    max_sharpe_portfolio as _max_sharpe_portfolio,
    min_vol_portfolio as _min_vol_portfolio,
    true_efficient_frontier as _true_efficient_frontier,
)


@st.cache_data(ttl=3600, show_spinner=False)
def calc_random_cloud(rets, risk_free=0.04):
    return _calc_random_cloud(rets, risk_free=risk_free)


@st.cache_data(ttl=3600, show_spinner=False)
def true_efficient_frontier(rets, risk_free=0.04, n_points=60,
                             max_weight=None, min_weight=0.0):
    return _true_efficient_frontier(rets, risk_free=risk_free, n_points=n_points,
                                    max_weight=max_weight, min_weight=min_weight)


@st.cache_data(ttl=3600, show_spinner=False)
def max_sharpe_portfolio(rets, risk_free=0.04, max_weight=None, min_weight=0.0):
    return _max_sharpe_portfolio(rets, risk_free=risk_free,
                                 max_weight=max_weight, min_weight=min_weight)


@st.cache_data(ttl=3600, show_spinner=False)
def min_vol_portfolio(rets, max_weight=None, min_weight=0.0):
    return _min_vol_portfolio(rets, max_weight=max_weight, min_weight=min_weight)
from analytics.rolling import rolling_sharpe, rolling_drawdown
from analytics.stress import run_all_stress
from analytics.backtest import compare_backtests, backtest_summary
from analytics.rebalancing import build_rebalancing_plan

from utils.formatting import badge, fmt_pct, fmt_val
from utils.components import (
    render_empty_state, render_audit_caption, render_section_title,
)
from ui.charts import (
    chart_sector_comparison, chart_ticker_donut,
    chart_drawdowns, chart_performance,
    chart_monte_carlo, chart_contributors,
    chart_correlation_matrix, chart_efficient_frontier,
    chart_rolling_sharpe, chart_rolling_drawdown,
    chart_backtest_comparison, chart_stress_results,
)


# ── Tab 1 : Allocation ────────────────────────────────────────────────────────

def render_tab_allocation(df_port: pd.DataFrame, comp_df: pd.DataFrame) -> None:
    unclassified = comp_df.attrs.get("unclassified_weight", 0)
    if unclassified > 0.05:
        st.info(
            f"ℹ️ {unclassified:.1%} du portefeuille est composé d'ETFs ou d'actifs sans secteur "
            f"(ex: SPY) — exclus du graphique sectoriel mais inclus dans le donut."
        )
    col_l, col_r = st.columns(2)
    with col_l:
        render_section_title("🏢", "Poids sectoriels", "vs S&P 500")
        st.plotly_chart(chart_sector_comparison(comp_df), use_container_width=True)
    with col_r:
        render_section_title("🎯", "Concentration par ticker", "Allocation actuelle")
        st.plotly_chart(chart_ticker_donut(df_port), use_container_width=True)


# ── Tab 2 : Risk ──────────────────────────────────────────────────────────────

def render_tab_risk(m: dict, port_rets: pd.Series, total_val: float,
                    mc_distribution: str = "normal", mc_t_df: int = 5) -> None:
    col_l, col_r = st.columns(2)

    with col_l:
        render_section_title("📉", "Historique des drawdowns", "Profondeur des replis")
        st.plotly_chart(chart_drawdowns(m["drawdowns"]), use_container_width=True)

        render_section_title("⚠️", "Métriques de perte", "Horizon 1 jour")
        c1, c2 = st.columns(2)
        c1.metric("VaR 95%",  f"{m['var_95']:.2%}")
        c2.metric("CVaR 95%", f"{m['cvar_95']:.2%}")
        st.caption(
            f"Dans 95 % des séances, la perte ne dépasse pas **{abs(m['var_95']):.2%}**. "
            f"Dans les 5 % pires cas, la perte moyenne est **{abs(m['cvar_95']):.2%}**."
        )
        with st.expander("En savoir plus"):
            st.markdown(
                f"- **VaR** : {METRIC_EXPLANATIONS['VaR 95%']}\n"
                f"- **CVaR** : {METRIC_EXPLANATIONS['CVaR 95%']}\n\n"
                "La CVaR mesure la perte **moyenne** dans les scénarios extrêmes — "
                "plus conservatrice que la VaR seule."
            )

    with col_r:
        label_dist = "Student-t" if mc_distribution == "t" else "Normale"
        render_section_title("🎲", "Monte Carlo",
                             f"500 trajectoires · 1 an · {label_dist}")
        mc_df = monte_carlo(port_rets, total_val,
                            distribution=mc_distribution, t_df=mc_t_df)
        st.plotly_chart(chart_monte_carlo(mc_df, total_val), use_container_width=True)

        mc_end = mc_df.iloc[-1]
        e1, e2, e3 = st.columns(3)
        e1.metric("Haussier (P95)", f"${mc_end['P95']:,.0f}",
                  f"{mc_end['P95']/total_val-1:+.1%}")
        e2.metric("Médian",         f"${mc_end['Médiane']:,.0f}",
                  f"{mc_end['Médiane']/total_val-1:+.1%}")
        e3.metric("Baissier (P5)",  f"${mc_end['P5']:,.0f}",
                  f"{mc_end['P5']/total_val-1:+.1%}", delta_color="inverse")


# ── Tab 3 : Performance & MPT ─────────────────────────────────────────────────

def render_tab_performance(
    m: dict, mpt: dict,
    bench_cum: pd.Series | None,
    benchmark: str,
    port_rets: pd.Series,
    rets: pd.DataFrame,
    df_port: pd.DataFrame,
) -> None:
    # Benchmark warning
    if bench_cum is None:
        st.warning(
            f"⚠️ Benchmark **{benchmark}** introuvable ou hors de la période sélectionnée. "
            "Les statistiques MPT (Alpha, Bêta, R, IR) ne sont pas disponibles."
        )
        render_section_title("🚀", "Performance cumulée", "")
        st.line_chart(m["cum"].rename("Portefeuille"))
    else:
        render_section_title("🚀", "Performance cumulée",
                             f"vs benchmark {benchmark}")
        st.plotly_chart(chart_performance(m["cum"], bench_cum, benchmark),
                        use_container_width=True)

    if mpt:
        render_section_title("📐", "Statistiques MPT",
                             f"Modèle Markowitz · benchmark {benchmark}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Bêta",          f"{mpt['beta']:.2f}")
        m2.metric("Alpha Annuel",  f"{mpt['alpha_ann']:+.1%}")
        m3.metric("Corrélation",   f"{mpt['r_val']:.2f}")
        m4.metric("Calmar",        f"{m['calmar']:.2f}")

        i1, i2, i3, i4 = st.columns(4)
        i1.metric("Information Ratio", f"{mpt.get('info_ratio', 0):.2f}")
        i2.metric("Tracking Error",    f"{mpt.get('tracking_error', 0):.1%}")
        if mpt.get("up_capture") is not None:
            i3.metric("Up Capture",   f"{mpt['up_capture']:.0%}")
        if mpt.get("down_capture") is not None:
            i4.metric("Down Capture", f"{mpt['down_capture']:.0%}")

        with st.expander("💡 Interprétation"):
            beta_txt  = "plus volatile que le marché" if mpt["beta"] > 1 else "moins volatile"
            r_txt     = "forte" if abs(mpt["r_val"]) > 0.8 else "modérée" if abs(mpt["r_val"]) > 0.5 else "faible"
            alpha_txt = "Surperformance" if mpt["alpha_ann"] > 0 else "Sous-performance"
            st.markdown(f"""
| Métrique | Valeur | Lecture |
|---|---|---|
| **Bêta** | {mpt['beta']:.2f} | Portefeuille {beta_txt} |
| **Alpha** | {mpt['alpha_ann']:+.1%}/an | {alpha_txt} vs {benchmark} après ajustement risque |
| **R** | {mpt['r_val']:.2f} | Corrélation {r_txt} avec {benchmark} |
| **Info Ratio** | {mpt.get('info_ratio', 0):.2f} | Qualité de l'alpha actif |
| **Tracking Error** | {mpt.get('tracking_error', 0):.1%} | Volatilité des écarts vs benchmark |
| **Sharpe** | {m['sharpe']:.2f} | {badge(m['sharpe'], 'Sharpe')} |
| **Sortino** | {m['sortino']:.2f} | {badge(m['sortino'], 'Sortino')} |
| **Calmar** | {m['calmar']:.2f} | {badge(m['calmar'], 'Calmar')} |
""")

    render_section_title("🏆", "Top contributeurs", "Sur les 30 derniers jours")
    contrib = top_contributors(df_port, rets, horizon=30)
    if not contrib.empty:
        st.plotly_chart(chart_contributors(contrib), use_container_width=True)
    else:
        st.info("Données insuffisantes pour les contributions récentes.")


# ── Tab 4 : Corrélations & Optimisation ──────────────────────────────────────

def render_tab_optimization(
    rets: pd.DataFrame,
    df_port: pd.DataFrame,
    risk_free: float,
    m: dict,
    max_weight: float | None = None,
    min_weight: float = 0.0,
    last_prices: pd.Series | None = None,
    total_val: float | None = None,
) -> None:
    valid_cols = [c for c in df_port["Symbol"].tolist() if c in rets.columns]
    port_only  = rets[valid_cols]

    # ── Correlation matrix ────────────────────────────────────────────────────
    render_section_title("🔗", "Matrice de corrélation",
                         "Mouvements croisés des actifs")
    if len(valid_cols) >= 2:
        st.plotly_chart(chart_correlation_matrix(port_only), use_container_width=True)
        st.caption(
            "Valeurs proches de **+1** = mouvements identiques (risque concentré). "
            "Valeurs proches de **0** ou **-1** = diversification réelle."
        )
    else:
        st.info("Au moins 2 actifs sont nécessaires pour calculer les corrélations.")

    st.divider()

    # ── Efficient Frontier ────────────────────────────────────────────────────
    render_section_title("🎯", "Frontière efficiente",
                         "Optimisation Markowitz · SLSQP")
    if max_weight and max_weight < 1.0:
        st.caption(f"Contrainte : aucune position au-delà de **{max_weight:.0%}** "
                   f"(et au moins **{min_weight:.0%}** chacune).")

    if len(valid_cols) < 2:
        st.info("Au moins 2 actifs sont nécessaires pour la frontière efficiente.")
        return

    with st.spinner("Calcul de la frontière efficiente..."):
        cloud       = calc_random_cloud(port_only, risk_free=risk_free)
        frontier    = true_efficient_frontier(port_only, risk_free=risk_free,
                                              max_weight=max_weight,
                                              min_weight=min_weight)
        max_sh      = max_sharpe_portfolio(port_only, risk_free=risk_free,
                                           max_weight=max_weight,
                                           min_weight=min_weight)
        min_v       = min_vol_portfolio(port_only,
                                        max_weight=max_weight,
                                        min_weight=min_weight)
        weights_now = df_port.set_index("Symbol")["W"].reindex(valid_cols).values
        pr_now      = port_only.dot(weights_now)
        current     = {
            "return":     float(pr_now.mean() * 252),
            "volatility": float(pr_now.std() * np.sqrt(252)),
        }

    st.plotly_chart(
        chart_efficient_frontier(cloud, frontier, current, max_sh, min_v),
        use_container_width=True,
    )

    # Optimal allocation table + rebalancing plan
    if max_sh:
        render_section_title("✨", "Allocation optimale", "Max Sharpe")
        c1, c2, c3 = st.columns(3)
        c1.metric("Sharpe optimal",    f"{max_sh['sharpe']:.2f}")
        c2.metric("Rendement attendu", f"{max_sh['return']:+.1%}")
        c3.metric("Volatilité",        f"{max_sh['volatility']:.1%}")

        opt_df = pd.DataFrame({
            "Ticker": list(max_sh["weights"].keys()),
            "Poids optimal": list(max_sh["weights"].values()),
            "Poids actuel": [
                df_port.set_index("Symbol")["W"].get(t, 0.0)
                for t in max_sh["weights"]
            ],
        })
        opt_df["Δ Poids"] = opt_df["Poids optimal"] - opt_df["Poids actuel"]
        opt_df = opt_df[opt_df["Poids optimal"] > 0.005].sort_values("Poids optimal",
                                                                    ascending=False)
        st.dataframe(
            opt_df.style.format(
                {"Poids optimal": "{:.1%}", "Poids actuel": "{:.1%}", "Δ Poids": "{:+.1%}"}
            ),
            use_container_width=True, hide_index=True,
        )
        st.caption("⚠️ Optimisation basée sur l'historique de prix — pas une recommandation d'investissement.")

        # Concrete rebalancing plan
        if last_prices is not None and total_val:
            with st.expander("🔄 Plan de rebalancing concret"):
                plan = build_rebalancing_plan(df_port, max_sh["weights"],
                                              last_prices, total_val)
                if plan.empty:
                    st.success("Votre allocation est déjà très proche de l'optimum — "
                               "aucun rebalancing significatif requis.")
                else:
                    st.dataframe(plan, use_container_width=True, hide_index=True)
                    st.caption("Seuils : transactions < 0.5% du portefeuille ignorées.")


# ── Tab 5 : Rolling & Stress ─────────────────────────────────────────────────

def render_tab_rolling_stress(
    port_rets: pd.Series,
    risk_free: float,
    weights: dict,
) -> None:
    """Rolling Sharpe / Drawdown + historical stress tests."""
    render_section_title("📈", "Métriques roulantes",
                         "Fenêtre glissante 90 jours")
    if len(port_rets) > 120:
        col_l, col_r = st.columns(2)
        with col_l:
            rs = rolling_sharpe(port_rets, risk_free=risk_free)
            st.plotly_chart(chart_rolling_sharpe(rs), use_container_width=True)
        with col_r:
            rd = rolling_drawdown(port_rets)
            st.plotly_chart(chart_rolling_drawdown(rd), use_container_width=True)
    else:
        render_empty_state("Pas assez d'historique",
                          "Il faut au moins 120 séances pour des métriques roulantes.",
                          "📉")

    st.divider()
    render_section_title("⚡", "Stress tests historiques",
                         "Crises passées rejouées")
    st.caption(
        "Replie les rendements réels du portefeuille pendant des crises passées. "
        "Si un ticker n'existait pas, on utilise le benchmark SPY comme proxy."
    )
    with st.spinner("Calcul des scénarios..."):
        stress_df = run_all_stress(weights)

    if stress_df.empty:
        st.warning("Aucun scénario n'a pu être chargé (problème réseau / yfinance).")
        return

    st.plotly_chart(chart_stress_results(stress_df), use_container_width=True)

    fmt = {"Rendement": "{:+.1%}", "Max DD": "{:.1%}"}
    st.dataframe(
        stress_df.style.format(fmt), use_container_width=True, hide_index=True,
    )


# ── Tab 6 : Backtest allocation optimale ─────────────────────────────────────

def render_tab_backtest(
    rets: pd.DataFrame,
    current_w: dict,
    target_w: dict,
    bench_rets: pd.Series | None,
    benchmark: str,
) -> None:
    render_section_title("🔁", "Backtest comparatif",
                         "Actuel vs Max Sharpe · rebalance trimestriel")
    st.caption(
        "Simulation : et si vous aviez détenu la cible Max-Sharpe sur la même période, "
        "rebalancée chaque trimestre ?"
    )

    if not target_w:
        st.info("Aucune cible optimale disponible — vérifiez l'onglet Optimisation.")
        return

    df = compare_backtests(rets, current_w, target_w, bench_rets, benchmark)
    if df.empty:
        st.warning("Données insuffisantes pour le backtest.")
        return

    st.plotly_chart(chart_backtest_comparison(df), use_container_width=True)

    # Summary table
    rows = []
    for col in df.columns:
        s = backtest_summary(df[col])
        if s:
            rows.append({
                "Stratégie":     col,
                "Rend. total":   f"{s['total_ret']:+.1%}",
                "CAGR":          f"{s['cagr']:+.1%}",
                "Volatilité":    f"{s['vol']:.1%}",
                "Sharpe":        f"{s['sharpe']:.2f}",
                "Max DD":        f"{s['max_dd']:.1%}",
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Tab 7 : Positions & Export ───────────────────────────────────────────────

def render_tab_details(merged: pd.DataFrame, m: dict, mpt: dict, benchmark: str) -> None:
    render_section_title("📋", "Inventaire détaillé",
                         "Toutes les positions et leurs fondamentaux")

    display_cols = [
        "Symbol", "Nom", "Qty", "Secteur", "Val", "W",
        "CostBasis", "P&L%",
        "P/E", "Fwd P/E", "P/B", "EV/EBITDA",
        "Beta", "ROE", "Marge nette", "Div. Yield", "D/E",
    ]
    # P&L computed if CostBasis present
    if "CostBasis" in merged.columns:
        merged = merged.copy()
        valid_pnl = merged["CostBasis"].notna() & (merged["CostBasis"] > 0)
        merged["P&L%"] = None
        merged.loc[valid_pnl, "P&L%"] = (
            merged.loc[valid_pnl, "Prix"] / merged.loc[valid_pnl, "CostBasis"] - 1
        )

    display_df = merged[[c for c in display_cols if c in merged.columns]]

    fmt = {
        "Val":        "${:,.0f}",
        "W":          "{:.1%}",
        "CostBasis":  "${:,.2f}",
        "P&L%":       "{:+.1%}",
        "P/E":        "{:.1f}",
        "Fwd P/E":    "{:.1f}",
        "P/B":        "{:.2f}",
        "EV/EBITDA":  "{:.1f}",
        "Beta":       "{:.2f}",
        "ROE":        "{:.1%}",
        "Marge nette":"{:.1%}",
        "Div. Yield": "{:.2%}",
        "D/E":        "{:.2f}",
    }
    st.dataframe(
        display_df.style.format({k: v for k, v in fmt.items() if k in display_df.columns},
                                na_rep="N/A"),
        use_container_width=True, hide_index=True,
    )

    st.divider()
    render_section_title("📤", "Exports", "CSV · Markdown")
    c1, c2 = st.columns(2)
    c1.download_button(
        "📥 Positions CSV",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="portfolio_positions.csv",
        mime="text/csv",
    )
    c2.download_button(
        "📄 Rapport Markdown",
        data=_build_md_report(display_df, m, mpt, benchmark).encode("utf-8"),
        file_name="rapport_portfolio.md",
        mime="text/markdown",
    )


def _build_md_report(df: pd.DataFrame, m: dict, mpt: dict, benchmark: str) -> str:
    rows = [
        "# Rapport de Portefeuille\n",
        "## Métriques\n",
        "| Métrique | Valeur |", "|---|---|",
        f"| Rendement Total | {m['total_ret']:+.1%} |",
        f"| CAGR | {m['cagr']:+.1%} |",
        f"| Volatilité | {m['vol']:.1%} |",
        f"| Sharpe | {m['sharpe']:.2f} |",
        f"| Sortino | {m['sortino']:.2f} |",
        f"| Calmar | {m['calmar']:.2f} |",
        f"| Max Drawdown | {m['max_dd']:.1%} |",
        f"| VaR 95% | {m['var_95']:.2%} |",
        f"| CVaR 95% | {m['cvar_95']:.2%} |",
    ]
    if mpt:
        rows += [
            f"| Bêta vs {benchmark} | {mpt['beta']:.2f} |",
            f"| Alpha Annuel | {mpt['alpha_ann']:+.1%} |",
            f"| Information Ratio | {mpt.get('info_ratio', 0):.2f} |",
            f"| Tracking Error | {mpt.get('tracking_error', 0):.1%} |",
        ]
    rows += ["", "## Positions\n"]
    try:
        rows.append(df.to_markdown(index=False))
    except Exception:
        rows.append(df.to_csv(index=False))
    return "\n".join(rows)
