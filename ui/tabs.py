"""
One render_tab_* function per portfolio tab.
Each receives only the data it needs — no global state.
"""
import streamlit as st
import pandas as pd

from config import METRIC_EXPLANATIONS
from analytics.monte_carlo import monte_carlo
from analytics.allocation import top_contributors
from analytics.optimization import calc_efficient_frontier, max_sharpe_portfolio, min_vol_portfolio
from utils.formatting import badge, fmt_pct, fmt_val
from ui.charts import (
    chart_sector_comparison, chart_ticker_donut,
    chart_drawdowns, chart_performance,
    chart_monte_carlo, chart_contributors,
    chart_correlation_matrix, chart_efficient_frontier,
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
        st.subheader("Poids Sectoriels vs S&P 500")
        st.plotly_chart(chart_sector_comparison(comp_df), use_container_width=True)
    with col_r:
        st.subheader("Concentration par Ticker")
        st.plotly_chart(chart_ticker_donut(df_port), use_container_width=True)


# ── Tab 2 : Risk ──────────────────────────────────────────────────────────────

def render_tab_risk(m: dict, port_rets: pd.Series, total_val: float) -> None:
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Historique des Drawdowns")
        st.plotly_chart(chart_drawdowns(m["drawdowns"]), use_container_width=True)

        st.subheader("Métriques de Perte — 1 jour")
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
        st.subheader("Monte Carlo — 500 trajectoires (1 an)")
        mc_df = monte_carlo(port_rets, total_val)
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
            "Les statistiques MPT (Alpha, Bêta, R) ne sont pas disponibles."
        )
        st.subheader("Performance Cumulée")
        st.line_chart(m["cum"].rename("Portefeuille"))
    else:
        st.subheader("Performance Cumulée vs Benchmark")
        st.plotly_chart(chart_performance(m["cum"], bench_cum, benchmark),
                        use_container_width=True)

    if mpt:
        st.subheader("Statistiques MPT")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Bêta",         f"{mpt['beta']:.2f}")
        m2.metric("Alpha Annuel", f"{mpt['alpha_ann']:+.1%}")
        m3.metric("Corrélation",  f"{mpt['r_val']:.2f}")
        m4.metric("Calmar",       f"{m['calmar']:.2f}")

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
| **Sharpe** | {m['sharpe']:.2f} | {badge(m['sharpe'], 'Sharpe')} |
| **Sortino** | {m['sortino']:.2f} | {badge(m['sortino'], 'Sortino')} |
| **Calmar** | {m['calmar']:.2f} | {badge(m['calmar'], 'Calmar')} |
""")

    st.subheader("Top Contributeurs (30 derniers jours)")
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
) -> None:
    valid_cols = [c for c in df_port["Symbol"].tolist() if c in rets.columns]
    port_only  = rets[valid_cols]

    # ── Correlation matrix ────────────────────────────────────────────────────
    st.subheader("Matrice de Corrélation")
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
    st.subheader("Frontière Efficiente & Optimisation")
    if len(valid_cols) < 2:
        st.info("Au moins 2 actifs sont nécessaires pour la frontière efficiente.")
        return

    with st.spinner("Calcul de la frontière efficiente..."):
        frontier    = calc_efficient_frontier(port_only, risk_free=risk_free)
        max_sh      = max_sharpe_portfolio(port_only, risk_free=risk_free)
        min_v       = min_vol_portfolio(port_only)
        weights_now = df_port.set_index("Symbol")["W"].reindex(valid_cols).values
        pr_now      = port_only.dot(weights_now)
        current     = {
            "return":     float(pr_now.mean() * 252),
            "volatility": float(pr_now.std() * np.sqrt(252)),
        }

    st.plotly_chart(
        chart_efficient_frontier(frontier, current, max_sh, min_v),
        use_container_width=True,
    )

    # Optimal allocation table
    if max_sh:
        st.subheader("Allocation optimale — Max Sharpe")
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
        opt_df = opt_df[opt_df["Poids optimal"] > 0.005].sort_values("Poids optimal", ascending=False)
        st.dataframe(
            opt_df.style.format(
                {"Poids optimal": "{:.1%}", "Poids actuel": "{:.1%}", "Δ Poids": "{:+.1%}"}
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("⚠️ Optimisation basée sur l'historique de prix — pas une recommandation d'investissement.")


# ── Tab 5 : Positions & Export ────────────────────────────────────────────────

def render_tab_details(merged: pd.DataFrame, m: dict, mpt: dict, benchmark: str) -> None:
    st.subheader("Inventaire du Portefeuille")

    display_cols = [
        "Symbol", "Nom", "Qty", "Secteur", "Val", "W",
        "P/E", "Fwd P/E", "P/B", "EV/EBITDA",
        "Beta", "ROE", "Marge nette", "Div. Yield", "D/E",
    ]
    display_df = merged[[c for c in display_cols if c in merged.columns]]

    fmt = {
        "Val":        "${:,.0f}",
        "W":          "{:.1%}",
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
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Export")
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
        ]
    rows += ["", "## Positions\n"]
    try:
        rows.append(df.to_markdown(index=False))
    except Exception:
        rows.append(df.to_csv(index=False))
    return "\n".join(rows)


# numpy needed for the optimization tab
import numpy as np
