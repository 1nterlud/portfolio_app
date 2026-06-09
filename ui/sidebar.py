import streamlit as st
from datetime import datetime, timedelta
from config import DEFAULT_PORTFOLIO, DEFAULT_RISK_FREE, DEFAULT_BENCHMARK, APP_NAME, __version__
from utils.parsing import parse_positions, parse_csv_positions
from utils.profiles import (
    list_profiles, save_profile, load_profile, delete_profile,
    export_profiles_json, import_profiles_json,
)
from utils.components import render_sidebar_brand


def render_sidebar() -> dict:
    """
    Render the full sidebar and return all inputs as a plain dict.
    The "page" key is always present: "portfolio" | "stock" | "compare" | "watchlist".
    """
    with st.sidebar:
        # ── Premium brand block ───────────────────────────────────────────────
        render_sidebar_brand(APP_NAME, __version__, logo_letter="P")
        st.divider()

        # ── Navigation ────────────────────────────────────────────────────────
        st.markdown("### Navigation")
        page_label = st.radio(
            "Navigation",
            ["📊  Portfolio Dashboard", "🔍  Stock Research",
             "⚖️  Compare Stocks", "👁️  Watchlist"],
            label_visibility="collapsed",
        )
        if "Portfolio" in page_label:
            page = "portfolio"
        elif "Research" in page_label:
            page = "stock"
        elif "Compare" in page_label:
            page = "compare"
        else:
            page = "watchlist"
        st.divider()

        # ── Global Refresh ────────────────────────────────────────────────────
        if st.button("🔄  Rafraîchir les données", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cache vidé — données rechargées au prochain run.", icon="🔄")

        st.divider()

        # ── Stock Research controls ───────────────────────────────────────────
        if page == "stock":
            st.markdown("### Recherche")
            ticker = st.text_input(
                "Ticker",
                value=st.session_state.get("sr_ticker", "AAPL"),
                placeholder="ex: AAPL, MSFT, NVDA",
                label_visibility="collapsed",
            ).upper().strip()
            analyze_btn = st.button("Analyser  →", type="primary", use_container_width=True)

            if analyze_btn and ticker:
                st.session_state["sr_ticker"]   = ticker
                st.session_state["sr_analyzed"] = True

            recent = st.session_state.get("recent_tickers", [])
            if ticker and analyze_btn and ticker not in recent:
                recent = [ticker] + recent[:4]
                st.session_state["recent_tickers"] = recent
            if recent:
                st.caption("Récents")
                st.code(" · ".join(recent), language=None)

            return {
                "page":        "stock",
                "ticker":      st.session_state.get("sr_ticker", ticker),
                "analyze_btn": st.session_state.get("sr_analyzed", False),
            }

        # ── Compare Stocks ───────────────────────────────────────────────────
        if page == "compare":
            st.markdown("### Comparer 2-4 tickers")
            tickers_raw = st.text_input(
                "Tickers (séparés par virgules)",
                value=st.session_state.get("cmp_tickers_raw", "AAPL, MSFT, GOOGL"),
                label_visibility="collapsed",
            )
            run = st.button("Comparer  →", type="primary", use_container_width=True)
            if run:
                st.session_state["cmp_tickers_raw"] = tickers_raw
                st.session_state["cmp_run"] = True
            return {"page": "compare", "tickers_raw": tickers_raw,
                    "run": st.session_state.get("cmp_run", False)}

        # ── Watchlist ────────────────────────────────────────────────────────
        if page == "watchlist":
            st.markdown("### Watchlist")
            current = st.session_state.get("watchlist", "AAPL, MSFT, NVDA, TSLA, SPY")
            new = st.text_area(
                "Tickers",
                value=current,
                height=120,
                placeholder="Un ticker par ligne ou séparés par virgules",
                label_visibility="collapsed",
            )
            if st.button("Mettre à jour", use_container_width=True):
                st.session_state["watchlist"] = new
            return {"page": "watchlist", "tickers_raw": new}

        # ── Portfolio Dashboard controls ──────────────────────────────────────
        st.markdown("### Positions")
        input_mode = st.radio(
            "Mode",
            ["✏️  Manuel", "📂  Upload CSV"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if input_mode == "✏️  Manuel":
            st.caption("`TICKER, Quantité[, Prix d'achat]` — une ligne par position")
            raw_input   = st.text_area(
                label="positions",
                value=st.session_state.get("portfolio_raw", DEFAULT_PORTFOLIO),
                height=175,
                label_visibility="collapsed",
            )
            st.session_state["portfolio_raw"] = raw_input
            df_port_raw = parse_positions(raw_input)
        else:
            st.caption("Colonnes : `Symbol`, `Qty` (+ `CostBasis` optionnel)")
            uploaded    = st.file_uploader("CSV", type=["csv"], label_visibility="collapsed")
            df_port_raw = parse_csv_positions(uploaded) if uploaded else None

        # ── Profiles ─────────────────────────────────────────────────────────
        with st.expander("💾  Profils sauvegardés"):
            existing = list_profiles()
            if existing:
                sel = st.selectbox("Charger un profil", ["—"] + existing,
                                   label_visibility="collapsed")
                c1, c2 = st.columns(2)
                if c1.button("📥 Charger", use_container_width=True):
                    if sel and sel != "—":
                        p = load_profile(sel)
                        if p:
                            st.session_state["portfolio_raw"]   = p.get("raw", "")
                            st.session_state["benchmark_input"] = p.get("benchmark",
                                                                       DEFAULT_BENCHMARK)
                            st.session_state["risk_free_input"] = p.get("risk_free",
                                                                       DEFAULT_RISK_FREE)
                            st.rerun()
                if c2.button("🗑️ Supprimer", use_container_width=True):
                    if sel and sel != "—":
                        delete_profile(sel)
                        st.rerun()

            new_name = st.text_input("Nom du profil", placeholder="ex: Croissance US")
            if st.button("💾 Sauvegarder", use_container_width=True):
                if new_name:
                    save_profile(new_name, {
                        "raw":       st.session_state.get("portfolio_raw", ""),
                        "benchmark": st.session_state.get("benchmark_input",
                                                          DEFAULT_BENCHMARK),
                        "risk_free": st.session_state.get("risk_free_input",
                                                          DEFAULT_RISK_FREE),
                    })
                    st.toast(f"Profil '{new_name}' enregistré.", icon="✅")

            export = export_profiles_json()
            st.download_button("📤 Export JSON", data=export,
                               file_name="portfolios.json",
                               mime="application/json",
                               use_container_width=True)
            up = st.file_uploader("📥 Importer JSON", type=["json"],
                                  label_visibility="collapsed", key="profile_upload")
            if up:
                added = import_profiles_json(up.read().decode("utf-8"))
                if added:
                    st.toast(f"{added} profil(s) importé(s).", icon="✅")

        st.divider()
        st.markdown("### Paramètres")
        risk_free_pct = st.slider(
            "Taux sans risque (%)", 0.0, 6.0,
            float(st.session_state.get("risk_free_input", DEFAULT_RISK_FREE)),
            step=0.25,
        )
        st.session_state["risk_free_input"] = risk_free_pct
        risk_free = risk_free_pct / 100

        benchmark = st.text_input(
            "Benchmark",
            value=st.session_state.get("benchmark_input", DEFAULT_BENCHMARK),
        ).upper().strip()
        st.session_state["benchmark_input"] = benchmark

        with st.expander("🔒  Contraintes d'optimisation"):
            max_w_pct = st.slider("Poids max par position (%)",
                                  5, 100, 30, step=5)
            min_w_pct = st.slider("Poids min par position (%)",
                                  0, 20, 0, step=1)

        st.divider()
        st.markdown("### Période d'analyse")
        c1, c2    = st.columns(2)
        start_date = c1.date_input("Début", value=datetime.now() - timedelta(days=365 * 5))
        end_date   = c2.date_input("Fin",   value=datetime.now())

        with st.expander("🎲  Options Monte Carlo"):
            mc_distribution = st.selectbox(
                "Distribution des shocks",
                ["normal", "t"],
                format_func=lambda x: "Normale (GBM)" if x == "normal" else "Student-t (fat tails)",
            )
            mc_t_df = st.slider("Degrés de liberté (Student-t)", 3, 30, 5) \
                if mc_distribution == "t" else 5

        st.divider()
        run_btn      = st.button("🚀  Lancer l'analyse", type="primary", use_container_width=True)
        validate_btn = st.button("✅  Vérifier les tickers", use_container_width=True)

    return {
        "page":         "portfolio",
        "df_port_raw":  df_port_raw,
        "risk_free":    risk_free,
        "benchmark":    benchmark,
        "start_date":   start_date,
        "end_date":     end_date,
        "run_btn":      run_btn,
        "validate_btn": validate_btn,
        "max_weight":   max_w_pct / 100,
        "min_weight":   min_w_pct / 100,
        "mc_distribution": mc_distribution,
        "mc_t_df":      mc_t_df,
    }
