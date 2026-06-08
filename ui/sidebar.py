import streamlit as st
from datetime import datetime, timedelta
from config import DEFAULT_PORTFOLIO, DEFAULT_RISK_FREE, DEFAULT_BENCHMARK
from utils.parsing import parse_positions, parse_csv_positions


def render_sidebar() -> dict:
    """
    Render the full sidebar and return all inputs as a plain dict.
    The "page" key is always present: "portfolio" | "stock".
    """
    with st.sidebar:
        st.markdown("## 📈 Portfolio Pro")
        st.divider()

        # ── Navigation ────────────────────────────────────────────────────────
        page_label = st.radio(
            "Navigation",
            ["📊 Portfolio Dashboard", "🔍 Stock Research"],
            label_visibility="collapsed",
        )
        page = "portfolio" if "Portfolio" in page_label else "stock"
        st.divider()

        # ── Stock Research controls ───────────────────────────────────────────
        if page == "stock":
            st.markdown("### 🔍 Recherche")
            ticker = st.text_input(
                "Ticker",
                value=st.session_state.get("sr_ticker", "AAPL"),
                placeholder="ex: AAPL, MSFT, NVDA",
                label_visibility="collapsed",
            ).upper().strip()
            analyze_btn = st.button("Analyser →", type="primary", use_container_width=True)

            if analyze_btn and ticker:
                st.session_state["sr_ticker"]   = ticker
                st.session_state["sr_analyzed"] = True

            return {
                "page":        "stock",
                "ticker":      st.session_state.get("sr_ticker", ticker),
                "analyze_btn": st.session_state.get("sr_analyzed", False),
            }

        # ── Portfolio Dashboard controls ──────────────────────────────────────
        st.markdown("### 📋 Positions")
        input_mode = st.radio(
            "Mode",
            ["✏️ Manuel", "📂 Upload CSV"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if input_mode == "✏️ Manuel":
            st.caption("`TICKER, Quantité` — une ligne par position")
            raw_input   = st.text_area(
                label="positions",
                value=DEFAULT_PORTFOLIO,
                height=175,
                label_visibility="collapsed",
            )
            df_port_raw = parse_positions(raw_input)
        else:
            st.caption("Colonnes requises : `Symbol` et `Qty`")
            uploaded    = st.file_uploader("CSV", type=["csv"], label_visibility="collapsed")
            df_port_raw = parse_csv_positions(uploaded) if uploaded else None

        st.divider()
        st.markdown("### ⚙️ Paramètres")
        risk_free = st.slider("Taux sans risque (%)", 0.0, 6.0, DEFAULT_RISK_FREE, step=0.25) / 100
        benchmark = st.text_input("Benchmark", value=DEFAULT_BENCHMARK).upper().strip()

        st.divider()
        st.markdown("### 📅 Période")
        c1, c2    = st.columns(2)
        start_date = c1.date_input("Début", value=datetime.now() - timedelta(days=365 * 5))
        end_date   = c2.date_input("Fin",   value=datetime.now())

        st.divider()
        run_btn      = st.button("🚀 Lancer l'analyse", type="primary", use_container_width=True)
        validate_btn = st.button("✅ Vérifier les tickers", use_container_width=True)

    return {
        "page":         "portfolio",
        "df_port_raw":  df_port_raw,
        "risk_free":    risk_free,
        "benchmark":    benchmark,
        "start_date":   start_date,
        "end_date":     end_date,
        "run_btn":      run_btn,
        "validate_btn": validate_btn,
    }
