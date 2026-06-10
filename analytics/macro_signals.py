"""
Macro interpretation — pure rule-based signals and regime from FRED series.
No Streamlit, no network, no AI: fixed thresholds in, French reading out.

Each signal carries:
  step        — which chapter of the macro story it belongs to
                ("croissance" | "inflation" | "fed" | "stress")
  tone        — success | warning | danger | info
  title       — short French headline
  message     — what the data says
  positioning — what it implies for an investor (systematic, educational)
"""
import pandas as pd


def yoy_change(s: pd.Series, periods: int = 12) -> pd.Series:
    """Year-over-year percent change (e.g., CPI index → inflation rate)."""
    if s is None or len(s) <= periods:
        return pd.Series(dtype=float)
    return (s / s.shift(periods) - 1) * 100


def _last(s: pd.Series) -> float | None:
    s = s.dropna() if s is not None else pd.Series(dtype=float)
    return float(s.iloc[-1]) if not s.empty else None


def _months_ago(s: pd.Series, months: int) -> float | None:
    s = s.dropna() if s is not None else pd.Series(dtype=float)
    if s.empty:
        return None
    cutoff = s.index[-1] - pd.DateOffset(months=months)
    past = s[s.index <= cutoff]
    return float(past.iloc[-1]) if not past.empty else None


def _sahm_gap(un: pd.Series) -> float | None:
    """Unemployment now minus its 12-month low. ≥ +0.5 = Sahm-rule trigger."""
    if un is None or un.dropna().empty:
        return None
    un = un.dropna()
    try:
        low = float(un[un.index >= un.index[-1] - pd.DateOffset(months=12)].min())
        return float(un.iloc[-1]) - low
    except Exception:
        return None


# ── Signals ───────────────────────────────────────────────────────────────────

def macro_signals(series: dict) -> list[dict]:
    """
    Build interpretive signals from a {label: pd.Series} dict.
    Recognized labels: "Spread 10a − 2a", "CPI (indice)", "VIX",
    "Fed Funds Rate", "Chômage US", "Croissance PIB réel",
    "Sentiment conso (UMich)".
    """
    out = []

    # ── 1. Croissance ─────────────────────────────────────────────────────────
    gdp = _last(series.get("Croissance PIB réel"))
    if gdp is not None:
        if gdp < 0:
            out.append({
                "step": "croissance", "tone": "danger",
                "title": "PIB en contraction",
                "message": f"Croissance du PIB réel à {gdp:+.1f}% (trimestre annualisé) — "
                           "l'économie se contracte.",
                "positioning": "Position défensive : consommation de base, santé, utilities. "
                               "Éviter les cycliques (industrie, conso discrétionnaire) dont "
                               "les profits chutent avec l'activité.",
            })
        elif gdp < 1.5:
            out.append({
                "step": "croissance", "tone": "warning",
                "title": "Croissance molle",
                "message": f"PIB réel à {gdp:+.1f}% — sous le potentiel américain (~2%).",
                "positioning": "Monter en qualité : entreprises à bilan solide et marges "
                               "stables. Réduire les small caps endettées, plus fragiles "
                               "quand l'activité ralentit.",
            })
        else:
            out.append({
                "step": "croissance", "tone": "success",
                "title": "Croissance solide",
                "message": f"PIB réel à {gdp:+.1f}% — au-dessus ou proche du potentiel.",
                "positioning": "Environnement porteur pour les actions, y compris cycliques. "
                               "Le risque actions est normalement rémunéré.",
            })

    gap = _sahm_gap(series.get("Chômage US"))
    un_now = _last(series.get("Chômage US"))
    if gap is not None and un_now is not None:
        if gap >= 0.5:
            out.append({
                "step": "croissance", "tone": "danger",
                "title": "Règle de Sahm déclenchée",
                "message": f"Chômage à {un_now:.1f}%, soit {gap:+.1f} pt au-dessus de son "
                           "plus bas 12 mois. Ce seuil (+0.5 pt) a signalé chaque récession "
                           "US depuis 1970, sans faux positif majeur.",
                "positioning": "Signal le plus sérieux du tableau : renforcer les défensives, "
                               "alléger les cycliques, et garder des obligations d'État comme "
                               "amortisseur. Historiquement la Fed baisse ses taux dans la foulée.",
            })
        else:
            out.append({
                "step": "croissance", "tone": "success",
                "title": "Marché de l'emploi stable",
                "message": f"Chômage à {un_now:.1f}%, à {gap:+.1f} pt de son plus bas 12 mois "
                           "— pas de dégradation rapide (règle de Sahm non déclenchée).",
                "positioning": "Pas de signal récessif par l'emploi. Aucun ajustement "
                               "défensif requis sur ce critère.",
            })

    sent = _last(series.get("Sentiment conso (UMich)"))
    if sent is not None:
        if sent < 65:
            out.append({
                "step": "croissance", "tone": "warning",
                "title": "Consommateur déprimé",
                "message": f"Sentiment UMichigan à {sent:.0f} (moyenne historique ~85). "
                           "La consommation représente ~68% du PIB américain.",
                "positioning": "Prudence sur la consommation discrétionnaire (retail, "
                               "loisirs, automobile). Paradoxe utile : un sentiment très bas "
                               "a souvent été un bon point d'entrée boursier — le pessimisme "
                               "est déjà dans les prix.",
            })
        else:
            out.append({
                "step": "croissance", "tone": "success",
                "title": "Consommateur confiant",
                "message": f"Sentiment UMichigan à {sent:.0f} — la consommation, moteur "
                           "de l'économie US, tient.",
                "positioning": "Favorable aux secteurs liés au consommateur.",
            })

    # ── 2. Inflation ──────────────────────────────────────────────────────────
    cpi = series.get("CPI (indice)")
    infl = _last(yoy_change(cpi)) if cpi is not None else None
    if infl is not None:
        if infl > 4:
            out.append({
                "step": "inflation", "tone": "danger",
                "title": "Inflation élevée",
                "message": f"CPI à {infl:.1f}% sur un an — plus du double de la cible Fed (2%). "
                           "Elle force la Fed à maintenir des taux élevés.",
                "positioning": "Privilégier les entreprises à pricing power (capables de monter "
                               "leurs prix) et les actifs réels (énergie, matières premières). "
                               "Éviter les obligations longues — l'inflation ronge leurs coupons "
                               "fixes — et la croissance non profitable, valorisée sur des "
                               "profits lointains.",
            })
        elif infl > 2.5:
            out.append({
                "step": "inflation", "tone": "warning",
                "title": "Inflation au-dessus de la cible",
                "message": f"CPI à {infl:.1f}% sur un an vs cible Fed de 2% — "
                           "désinflation incomplète.",
                "positioning": "Ne pas allonger la duration obligataire tant que la tendance "
                               "ne converge pas vers 2%. Côté actions, neutre.",
            })
        else:
            out.append({
                "step": "inflation", "tone": "success",
                "title": "Inflation maîtrisée",
                "message": f"CPI à {infl:.1f}% sur un an — dans la zone de confort de la Fed.",
                "positioning": "Feu vert pour les obligations (coupons réels positifs) et les "
                               "actions de croissance, premières bénéficiaires de taux bas.",
            })

    # ── 3. Fed & courbe ───────────────────────────────────────────────────────
    spread = _last(series.get("Spread 10a − 2a"))
    if spread is not None:
        if spread < 0:
            out.append({
                "step": "fed", "tone": "danger",
                "title": "Courbe des taux inversée",
                "message": f"Spread 10a−2a à {spread:+.2f} pt. Le marché obligataire price "
                           "des baisses de taux futures — il anticipe un ralentissement. "
                           "Chaque récession US depuis 1976 a été précédée d'une inversion.",
                "positioning": "Réduire progressivement le bêta du portefeuille (pas brutalement : "
                               "le délai inversion → récession a varié de 6 à 24 mois). Les "
                               "obligations d'État longues profitent ensuite de la baisse des taux.",
            })
        elif spread < 0.5:
            out.append({
                "step": "fed", "tone": "warning",
                "title": "Courbe des taux plate",
                "message": f"Spread 10a−2a à {spread:+.2f} pt — le coussin avant inversion "
                           "est mince.",
                "positioning": "Pas d'action immédiate, mais resserrer les critères de qualité "
                               "sur les nouvelles positions et surveiller le spread chaque mois.",
            })
        else:
            out.append({
                "step": "fed", "tone": "success",
                "title": "Courbe des taux normale",
                "message": f"Spread 10a−2a à {spread:+.2f} pt — pente positive, le marché "
                           "obligataire ne signale pas de récession.",
                "positioning": "Pas de contrainte côté courbe — le plan d'allocation normal "
                               "s'applique.",
            })

    ff_now  = _last(series.get("Fed Funds Rate"))
    ff_past = _months_ago(series.get("Fed Funds Rate", pd.Series(dtype=float)), 6)
    if ff_now is not None and ff_past is not None:
        diff = ff_now - ff_past
        if diff > 0.25:
            out.append({
                "step": "fed", "tone": "warning",
                "title": "Cycle de resserrement",
                "message": f"Fed Funds à {ff_now:.2f}% ({diff:+.2f} pt sur 6 mois) — la Fed "
                           "durcit pour freiner l'inflation.",
                "positioning": "Vent contraire pour la croissance long-duration (tech non "
                               "profitable) et les small caps endettées à taux variable. Le "
                               "cash et les maturités courtes redeviennent rémunérateurs.",
            })
        elif diff < -0.25:
            out.append({
                "step": "fed", "tone": "info",
                "title": "Cycle d'assouplissement",
                "message": f"Fed Funds à {ff_now:.2f}% ({diff:+.2f} pt sur 6 mois) — "
                           "la Fed baisse ses taux.",
                "positioning": "Hors récession, les baisses de taux sont historiquement "
                               "favorables aux actions. La duration obligataire en profite. "
                               "Question clé : la Fed baisse-t-elle par confort (inflation "
                               "vaincue → bullish) ou par urgence (récession → défensif) ? "
                               "Croiser avec l'étape Croissance.",
            })
        else:
            out.append({
                "step": "fed", "tone": "info",
                "title": "Politique monétaire stable",
                "message": f"Fed Funds à {ff_now:.2f}% — pas de mouvement notable sur 6 mois.",
                "positioning": "Pas de signal directionnel — l'attention se porte sur "
                               "l'inflation et la croissance pour anticiper le prochain mouvement.",
            })

    # ── 4. Stress de marché ───────────────────────────────────────────────────
    vix = _last(series.get("VIX"))
    if vix is not None:
        if vix > 30:
            out.append({
                "step": "stress", "tone": "danger",
                "title": "Stress de marché élevé",
                "message": f"VIX à {vix:.0f} — régime de panique. Les corrélations montent : "
                           "tout baisse ensemble, la diversification protège moins.",
                "positioning": "Ne pas vendre dans la panique — les pires journées sont suivies "
                               "des meilleurs rebonds. Rééquilibrer méthodiquement vers les poids "
                               "cibles (acheter ce qui a le plus baissé), aucun levier. Le cash "
                               "déployé pendant les pics de VIX a historiquement bien payé.",
            })
        elif vix > 20:
            out.append({
                "step": "stress", "tone": "warning",
                "title": "Marché nerveux",
                "message": f"VIX à {vix:.0f} — au-dessus de la moyenne historique (~19).",
                "positioning": "Vérifier la concentration du portefeuille (positions > 25%, "
                               "secteur > 40%) — c'est elle qui fait mal en cas de pic de "
                               "volatilité. Pas de levier.",
            })
        else:
            out.append({
                "step": "stress", "tone": "success",
                "title": "Volatilité contenue",
                "message": f"VIX à {vix:.0f} — régime calme.",
                "positioning": "Conditions normales d'exécution. Moment idéal pour rééquilibrer "
                               "ou ajuster le portefeuille à froid, sans pression.",
            })

    return out


# ── Regime synthesis ──────────────────────────────────────────────────────────

REGIME_PLAYBOOKS = {
    "Expansion": {
        "tone": "success",
        "resume": "Croissance correcte, pas de signal récessif, stress contenu. "
                  "Le scénario central est la poursuite du cycle.",
        "favoriser": ["Actions larges (le bêta de marché est rémunéré)",
                      "Cycliques et small caps de qualité",
                      "Rester investi — le market timing coûte cher en expansion"],
        "eviter":    ["Sur-couverture défensive coûteuse",
                      "Excès de cash non investi"],
        "surveiller": ["Inflation (un dérapage forcerait la Fed à durcir)",
                       "Spread 10a−2a (un aplatissement = fin de cycle qui approche)"],
    },
    "Fin de cycle": {
        "tone": "warning",
        "resume": "La courbe des taux est inversée mais l'économie tient encore. "
                  "Historiquement, il reste 6 à 24 mois avant la récession éventuelle.",
        "favoriser": ["Qualité : bilans solides, marges stables, faible dette",
                      "Défensives en renfort progressif (santé, conso de base)",
                      "Obligations d'État longues (profitent de la future baisse des taux)"],
        "eviter":    ["Augmenter le bêta ou le levier à ce stade",
                      "Small caps endettées et croissance non profitable"],
        "surveiller": ["Règle de Sahm (chômage) — le déclencheur le plus fiable",
                       "Re-pentification de la courbe (souvent juste avant la récession)"],
    },
    "Ralentissement": {
        "tone": "warning",
        "resume": "La croissance faiblit sans signal de récession imminente. "
                  "Phase de transition où la qualité fait la différence.",
        "favoriser": ["Qualité et dividendes croissants",
                      "Défensives (santé, conso de base, utilities)",
                      "Duration obligataire modérée"],
        "eviter":    ["Cycliques agressives (industrie, conso discrétionnaire)",
                      "Entreprises à refinancement court terme"],
        "surveiller": ["PIB et chômage (confirmation ou rebond)",
                       "Pivots de la Fed (l'assouplissement soutiendrait les actions)"],
    },
    "Surchauffe inflationniste": {
        "tone": "danger",
        "resume": "Inflation élevée avec Fed en durcissement. Les taux montent, "
                  "les valorisations compressent — surtout la croissance long-duration.",
        "favoriser": ["Pricing power : entreprises capables de monter leurs prix",
                      "Actifs réels : énergie, matières premières",
                      "Maturités courtes et cash (enfin rémunérés)"],
        "eviter":    ["Obligations longues (l'inflation détruit les coupons fixes)",
                      "Croissance non profitable valorisée sur des profits lointains"],
        "surveiller": ["CPI mensuel (la tendance vers 2% conditionne le pivot Fed)",
                       "Courbe des taux (le durcissement finit souvent par l'inverser)"],
    },
    "Stress de marché": {
        "tone": "danger",
        "resume": "Volatilité de panique (VIX > 30). Les corrélations montent, "
                  "la discipline compte plus que la prévision.",
        "favoriser": ["Rééquilibrage méthodique vers les poids cibles",
                      "Déploiement progressif du cash (pas tout d'un coup)",
                      "Qualité bradée par la panique"],
        "eviter":    ["Vendre dans la panique (les pires jours précèdent les meilleurs)",
                      "Tout levier ou produit à volatilité"],
        "surveiller": ["VIX repassant sous 25 (stabilisation)",
                       "Réponse Fed/Trésor (les interventions marquent souvent le creux)"],
    },
    "Risque de récession": {
        "tone": "danger",
        "resume": "Les signaux les plus fiables (règle de Sahm, contraction du PIB) "
                  "sont déclenchés. Préserver le capital devient prioritaire.",
        "favoriser": ["Défensives : conso de base, santé, utilities",
                      "Obligations d'État longues si l'inflation est maîtrisée",
                      "Cash de réserve pour acheter le creux quand il viendra"],
        "eviter":    ["Cycliques, small caps endettées, high yield",
                      "Rattraper les couteaux qui tombent sans plan d'entrée"],
        "surveiller": ["Assouplissement Fed agressif (précède souvent le creux boursier)",
                       "Stabilisation du chômage (le creux actions arrive avant celui de l'économie)"],
    },
}


def macro_regime(series: dict) -> dict:
    """
    Combine the systematic readings into one regime + playbook.
    Fixed rule order (most severe first) — fully explainable, no scoring black box.
    Returns {regime, tone, resume, raisons, favoriser, eviter, surveiller}.
    """
    gdp    = _last(series.get("Croissance PIB réel"))
    gap    = _sahm_gap(series.get("Chômage US"))
    spread = _last(series.get("Spread 10a − 2a"))
    vix    = _last(series.get("VIX"))
    cpi    = series.get("CPI (indice)")
    infl   = _last(yoy_change(cpi)) if cpi is not None else None
    ff_now  = _last(series.get("Fed Funds Rate"))
    ff_past = _months_ago(series.get("Fed Funds Rate", pd.Series(dtype=float)), 6)
    tightening = (ff_now is not None and ff_past is not None
                  and ff_now - ff_past > 0.25)

    raisons = []

    # Rule order: most severe condition wins.
    if (gap is not None and gap >= 0.5) or (gdp is not None and gdp < 0):
        regime = "Risque de récession"
        if gap is not None and gap >= 0.5:
            raisons.append(f"Règle de Sahm déclenchée (chômage {gap:+.1f} pt vs plus bas 12 mois)")
        if gdp is not None and gdp < 0:
            raisons.append(f"PIB réel en contraction ({gdp:+.1f}%)")
    elif vix is not None and vix > 30:
        regime = "Stress de marché"
        raisons.append(f"VIX à {vix:.0f} (> 30)")
    elif infl is not None and infl > 4 and tightening:
        regime = "Surchauffe inflationniste"
        raisons.append(f"Inflation à {infl:.1f}% avec Fed en resserrement")
    elif spread is not None and spread < 0:
        regime = "Fin de cycle"
        raisons.append(f"Courbe des taux inversée ({spread:+.2f} pt)")
    elif (gdp is not None and gdp < 1.5):
        regime = "Ralentissement"
        raisons.append(f"Croissance du PIB sous le potentiel ({gdp:+.1f}%)")
    else:
        regime = "Expansion"
        if gdp is not None:
            raisons.append(f"Croissance correcte ({gdp:+.1f}%)")
        if spread is not None and spread >= 0:
            raisons.append(f"Courbe des taux non inversée ({spread:+.2f} pt)")
        if vix is not None and vix <= 30:
            raisons.append(f"Stress de marché contenu (VIX {vix:.0f})")
        if not raisons:
            raisons.append("Aucun signal d'alerte sur les données disponibles")

    pb = REGIME_PLAYBOOKS[regime]
    return {
        "regime":     regime,
        "tone":       pb["tone"],
        "resume":     pb["resume"],
        "raisons":    raisons,
        "favoriser":  pb["favoriser"],
        "eviter":     pb["eviter"],
        "surveiller": pb["surveiller"],
    }
