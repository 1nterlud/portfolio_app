"""
Macro page — a systematic, ordered reading of the US macro environment.
Story: 1. Croissance → 2. Inflation → 3. Fed & taux → 4. Stress → 5. Synthèse.
Every reading is rule-based (analytics/macro_signals.py) and explained in French
so the page is usable without any financial background.
"""
import streamlit as st
import pandas as pd

from data.macro import fetch_macro_category, macro_available, MACRO_CATALOG
from analytics.macro_signals import macro_signals, macro_regime, yoy_change
from ui.charts import chart_macro_lines
from utils.components import (
    render_page_hero, render_empty_state, render_section_title,
)

_TONE_ICON  = {"danger": "🔴", "warning": "🟠", "success": "🟢", "info": "🔵"}
_TONE_BOX   = {"danger": st.error, "warning": st.warning,
               "success": st.success, "info": st.info}


def _render_signals(signals: list[dict], step: str) -> None:
    """Render the systematic reading + positioning for one chapter."""
    for s in [x for x in signals if x["step"] == step]:
        box = _TONE_BOX.get(s["tone"], st.info)
        box(f"**{s['title']}** — {s['message']}\n\n"
            f"🧭 **Comment se positionner :** {s['positioning']}")


def render_macro(inputs: dict) -> None:
    render_page_hero(
        eyebrow="Environnement macro",
        title="Macro Dashboard",
        subtitle="Une lecture systématique en 5 étapes : croissance, inflation, Fed, "
                 "stress de marché, puis synthèse et positionnement.",
        pills=[("1️⃣", "Croissance"), ("2️⃣", "Inflation"),
               ("3️⃣", "Fed & Taux"), ("4️⃣", "Stress"), ("5️⃣", "Synthèse")],
    )

    if not macro_available():
        render_empty_state(
            "Clé FRED manquante",
            "Cette page utilise l'API gratuite de la Federal Reserve (FRED). "
            "Créez une clé sur fred.stlouisfed.org puis ajoutez `FRED_API_KEY` "
            "dans `.streamlit/secrets.toml` (local) ou dans les Secrets Streamlit Cloud.",
            "🔑",
        )
        return

    with st.expander("📖 Comment lire cette page (méthode)", expanded=False):
        st.markdown("""
La lecture macro se fait **toujours dans le même ordre** — chaque étape conditionne la suivante :

1. **Croissance** — l'économie accélère ou ralentit ? C'est elle qui fait les profits des entreprises.
2. **Inflation** — sous contrôle ou pas ? C'est elle qui dicte le comportement de la Fed.
3. **Fed & taux** — la banque centrale aide ou freine ? Les taux sont la gravité des valorisations.
4. **Stress de marché** — le marché est-il calme ou en panique ? Ça détermine *comment* agir.
5. **Synthèse** — les 4 lectures se combinent en un **régime**, et chaque régime a son plan d'action.

Toutes les règles sont **fixes et transparentes** (seuils affichés dans chaque encadré) —
aucune prédiction, aucune boîte noire. Usage pédagogique : ce n'est pas un conseil d'investissement.
""")

    years = st.radio("Période des graphiques", [3, 5, 10], index=1, horizontal=True,
                     format_func=lambda y: f"{y} ans")

    with st.spinner("Chargement des données FRED..."):
        data = {cat: fetch_macro_category(cat, years) for cat in MACRO_CATALOG}

    all_series = {k: v for cat in data.values() for k, v in cat.items()}
    if not any(not s.empty for s in all_series.values()):
        st.warning("Impossible de récupérer les données FRED. "
                   "Vérifiez votre clé API ou réessayez plus tard.")
        return

    signals = macro_signals(all_series)
    regime  = macro_regime(all_series)

    # ── Verdict en tête (l'ordre de lecture reste détaillé en dessous) ────────
    icon = _TONE_ICON.get(regime["tone"], "")
    _TONE_BOX.get(regime["tone"], st.info)(
        f"### {icon} Régime actuel : {regime['regime']}\n{regime['resume']}\n\n"
        f"*Détail de la lecture étape par étape ci-dessous — synthèse et plan "
        f"d'action complets à l'étape 5.*"
    )
    st.divider()

    # ════ ÉTAPE 1 : CROISSANCE ════════════════════════════════════════════════
    render_section_title("1️⃣", "La croissance",
                         "L'économie fait-elle des profits ?")
    st.markdown(
        "**Pourquoi commencer ici :** les profits des entreprises suivent l'activité "
        "économique. PIB en contraction = profits en baisse = marchés sous pression, "
        "quoi qu'il arrive ailleurs. Trois jauges : le **PIB** (la production), le "
        "**chômage** (le signal le plus fiable de retournement, via la règle de Sahm), "
        "et le **sentiment des consommateurs** (~68% du PIB américain)."
    )
    _render_signals(signals, "croissance")

    real = data["Économie réelle"]
    c1, c2 = st.columns(2)
    gdp = real.get("Croissance PIB réel", pd.Series(dtype=float))
    if not gdp.empty:
        with c1:
            st.plotly_chart(chart_macro_lines({"PIB réel (T/T annualisé)": gdp},
                                              "Croissance du PIB réel",
                                              y_title="%", hline=0.0),
                            use_container_width=True)
            st.caption("Sous la ligne 0 = contraction. Potentiel américain ≈ 2%/an.")
    un = real.get("Chômage US", pd.Series(dtype=float))
    if not un.empty:
        with c2:
            st.plotly_chart(chart_macro_lines({"Chômage US": un},
                                              "Taux de chômage", y_title="%"),
                            use_container_width=True)
            st.caption("Règle de Sahm : +0.5 pt au-dessus du plus bas 12 mois = "
                       "signal de récession (fiable depuis 1970).")
    sent = real.get("Sentiment conso (UMich)", pd.Series(dtype=float))
    if not sent.empty:
        st.plotly_chart(chart_macro_lines({"Sentiment consommateur": sent},
                                          "Sentiment consommateur (UMichigan)",
                                          y_title="indice", hline=85.0),
                        use_container_width=True)
        st.caption("Ligne pointillée = moyenne historique (~85). Très bas = "
                   "consommation fragile… mais souvent bon point d'entrée boursier.")
    st.divider()

    # ════ ÉTAPE 2 : INFLATION ═════════════════════════════════════════════════
    render_section_title("2️⃣", "L'inflation",
                         "Le chien de garde qui dicte la Fed")
    st.markdown(
        "**Pourquoi en deuxième :** l'inflation décide de tout le reste. Au-dessus de "
        "la cible de **2%**, la Fed est obligée de garder des taux élevés même si "
        "l'économie souffre. Le **Core CPI** (hors énergie et alimentation) montre la "
        "tendance de fond — c'est lui que la Fed regarde."
    )
    _render_signals(signals, "inflation")

    infl_data = data["Inflation"]
    yoy = {}
    for label, s in infl_data.items():
        y = yoy_change(s).dropna()
        if not y.empty:
            yoy[label.replace("(indice)", "YoY")] = y
    if yoy:
        st.plotly_chart(chart_macro_lines(yoy, "Inflation en glissement annuel",
                                          y_title="%", hline=2.0),
                        use_container_width=True)
        st.caption("Ligne pointillée = cible Fed (2%). La distance à cette ligne "
                   "mesure la pression sur la Fed.")
    st.divider()

    # ════ ÉTAPE 3 : FED & TAUX ════════════════════════════════════════════════
    render_section_title("3️⃣", "La Fed et la courbe des taux",
                         "La gravité des valorisations")
    st.markdown(
        "**Pourquoi en troisième :** les taux d'intérêt sont la gravité de la finance — "
        "plus ils montent, plus les valorisations compressent. Deux lectures : la "
        "**direction de la Fed** (resserre ou assouplit ?) et la **courbe des taux** "
        "(spread 10 ans − 2 ans). Une courbe **inversée** (spread < 0) signifie que le "
        "marché obligataire anticipe des baisses de taux futures — donc un ralentissement. "
        "Ce signal a précédé **chaque récession US depuis 1976**."
    )
    _render_signals(signals, "fed")

    rates = data["Taux & Courbe"]
    curve = {k: rates[k] for k in ("Fed Funds Rate", "Treasury 2 ans",
                                   "Treasury 10 ans", "Mortgage 30 ans")
             if k in rates and not rates[k].empty}
    c1, c2 = st.columns(2)
    if curve:
        with c1:
            st.plotly_chart(chart_macro_lines(curve, "Taux directeurs et de marché",
                                              y_title="%"),
                            use_container_width=True)
    spread = rates.get("Spread 10a − 2a", pd.Series(dtype=float))
    if not spread.empty:
        with c2:
            st.plotly_chart(chart_macro_lines({"Spread 10a − 2a": spread},
                                              "Courbe des taux : spread 10a − 2a",
                                              y_title="pt", hline=0.0),
                            use_container_width=True)
            st.caption("Sous 0 = courbe inversée. Le délai inversion → récession a "
                       "historiquement varié de 6 à 24 mois.")
    st.divider()

    # ════ ÉTAPE 4 : STRESS DE MARCHÉ ══════════════════════════════════════════
    render_section_title("4️⃣", "Le stress de marché",
                         "Décide du COMMENT, pas du QUOI")
    st.markdown(
        "**Pourquoi en dernier :** les trois premières étapes disent *quoi* faire ; le "
        "VIX dit *comment* le faire. Marché calme (VIX < 20) = on peut ajuster "
        "tranquillement. Marché en panique (VIX > 30) = surtout ne rien vendre dans "
        "l'urgence — c'est statistiquement le pire moment."
    )
    _render_signals(signals, "stress")

    mkt = data["Marchés"]
    c1, c2 = st.columns(2)
    vix = mkt.get("VIX", pd.Series(dtype=float))
    if not vix.empty:
        with c1:
            st.plotly_chart(chart_macro_lines({"VIX": vix},
                                              "VIX — volatilité implicite S&P 500",
                                              y_title="pt", hline=20.0),
                            use_container_width=True)
            st.caption("< 20 calme · 20-30 nerveux · > 30 panique. Moyenne ~19.")
    usd = mkt.get("Dollar Index (broad)", pd.Series(dtype=float))
    if not usd.empty:
        with c2:
            st.plotly_chart(chart_macro_lines({"Dollar Index": usd},
                                              "Dollar US (indice large)",
                                              y_title="indice"),
                            use_container_width=True)
            st.caption("Dollar fort = vent contraire pour les multinationales US "
                       "et les marchés émergents.")
    st.divider()

    # ════ ÉTAPE 5 : SYNTHÈSE & POSITIONNEMENT ═════════════════════════════════
    render_section_title("5️⃣", "Synthèse : le régime et le plan",
                         "Les 4 lectures combinées")
    st.markdown(
        "**La règle de combinaison** (du plus grave au moins grave — la première "
        "condition remplie l'emporte) :\n\n"
        "| Priorité | Condition | Régime |\n"
        "|---|---|---|\n"
        "| 1 | Règle de Sahm déclenchée **ou** PIB < 0 | 🔴 Risque de récession |\n"
        "| 2 | VIX > 30 | 🔴 Stress de marché |\n"
        "| 3 | Inflation > 4% **et** Fed en resserrement | 🔴 Surchauffe inflationniste |\n"
        "| 4 | Courbe des taux inversée | 🟠 Fin de cycle |\n"
        "| 5 | PIB < 1.5% | 🟠 Ralentissement |\n"
        "| 6 | Aucune des conditions ci-dessus | 🟢 Expansion |\n"
    )

    icon = _TONE_ICON.get(regime["tone"], "")
    _TONE_BOX.get(regime["tone"], st.info)(
        f"### {icon} Régime actuel : {regime['regime']}\n\n"
        f"{regime['resume']}\n\n"
        f"**Pourquoi ce régime :** " + " · ".join(regime["raisons"])
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### ✅ Favoriser")
        for item in regime["favoriser"]:
            st.markdown(f"- {item}")
    with c2:
        st.markdown("#### ❌ Éviter")
        for item in regime["eviter"]:
            st.markdown(f"- {item}")
    with c3:
        st.markdown("#### 👁️ Surveiller")
        for item in regime["surveiller"]:
            st.markdown(f"- {item}")

    st.divider()
    st.warning(
        "⚠️ **Cadre pédagogique, pas un conseil d'investissement.** Ces règles décrivent "
        "des régularités historiques américaines — elles peuvent échouer, et chaque "
        "situation a ses spécificités. Le positionnement proposé est une grille de "
        "lecture systématique, pas une recommandation personnalisée."
    )
    st.caption("Source : FRED, Federal Reserve Bank of St. Louis. Données en cache 1 h — "
               "bouton 🔄 dans la sidebar pour forcer le rechargement.")
