"""
Macro interpretation — pure rule-based signals from FRED series.
No Streamlit, no network: takes series/values, returns French-language signals.
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


def macro_signals(series: dict) -> list[dict]:
    """
    Build interpretive signals from a {label: pd.Series} dict.
    Recognized labels: "Spread 10a − 2a", "CPI (indice)", "VIX",
    "Fed Funds Rate", "Chômage US".
    Returns [{tone: success|warning|danger|info, title, message}, ...].
    """
    out = []

    # ── Yield curve ───────────────────────────────────────────────────────────
    spread = _last(series.get("Spread 10a − 2a"))
    if spread is not None:
        if spread < 0:
            out.append({
                "tone": "danger", "title": "Courbe des taux inversée",
                "message": f"Spread 10a−2a à {spread:+.2f} pt. Une inversion prolongée "
                           "a historiquement précédé chaque récession US depuis 1976.",
            })
        elif spread < 0.5:
            out.append({
                "tone": "warning", "title": "Courbe des taux plate",
                "message": f"Spread 10a−2a à {spread:+.2f} pt — faible marge avant inversion.",
            })
        else:
            out.append({
                "tone": "success", "title": "Courbe des taux normale",
                "message": f"Spread 10a−2a à {spread:+.2f} pt — pente positive, "
                           "pas de signal de récession par la courbe.",
            })

    # ── Inflation (CPI YoY) ───────────────────────────────────────────────────
    cpi = series.get("CPI (indice)")
    infl = _last(yoy_change(cpi)) if cpi is not None else None
    if infl is not None:
        if infl > 4:
            out.append({
                "tone": "danger", "title": "Inflation élevée",
                "message": f"CPI à {infl:.1f}% sur un an — bien au-dessus de la cible "
                           "Fed de 2%. Pression sur les valorisations actions et obligations.",
            })
        elif infl > 2.5:
            out.append({
                "tone": "warning", "title": "Inflation au-dessus de la cible",
                "message": f"CPI à {infl:.1f}% sur un an vs cible Fed de 2%.",
            })
        else:
            out.append({
                "tone": "success", "title": "Inflation maîtrisée",
                "message": f"CPI à {infl:.1f}% sur un an — proche de la cible Fed de 2%.",
            })

    # ── VIX regime ────────────────────────────────────────────────────────────
    vix = _last(series.get("VIX"))
    if vix is not None:
        if vix > 30:
            out.append({
                "tone": "danger", "title": "Stress de marché élevé",
                "message": f"VIX à {vix:.0f} — régime de forte volatilité, "
                           "les corrélations entre actifs montent en période de stress.",
            })
        elif vix > 20:
            out.append({
                "tone": "warning", "title": "Marché nerveux",
                "message": f"VIX à {vix:.0f} — volatilité au-dessus de la moyenne historique (~19).",
            })
        else:
            out.append({
                "tone": "success", "title": "Volatilité contenue",
                "message": f"VIX à {vix:.0f} — régime calme.",
            })

    # ── Fed cycle (direction over 6 months) ───────────────────────────────────
    ff_now  = _last(series.get("Fed Funds Rate"))
    ff_past = _months_ago(series.get("Fed Funds Rate", pd.Series(dtype=float)), 6)
    if ff_now is not None and ff_past is not None:
        diff = ff_now - ff_past
        if diff > 0.25:
            out.append({
                "tone": "info", "title": "Cycle de resserrement",
                "message": f"Fed Funds à {ff_now:.2f}% ({diff:+.2f} pt sur 6 mois) — "
                           "politique monétaire en durcissement.",
            })
        elif diff < -0.25:
            out.append({
                "tone": "info", "title": "Cycle d'assouplissement",
                "message": f"Fed Funds à {ff_now:.2f}% ({diff:+.2f} pt sur 6 mois) — "
                           "la Fed baisse ses taux, historiquement favorable aux actions "
                           "hors récession.",
            })
        else:
            out.append({
                "tone": "info", "title": "Politique monétaire stable",
                "message": f"Fed Funds à {ff_now:.2f}% — pas de mouvement notable sur 6 mois.",
            })

    # ── Sahm-rule approximation (unemployment momentum) ──────────────────────
    un = series.get("Chômage US")
    if un is not None and not un.dropna().empty:
        un = un.dropna()
        try:
            low_12m = float(un[un.index >= un.index[-1] - pd.DateOffset(months=12)].min())
            now     = float(un.iloc[-1])
            if now - low_12m >= 0.5:
                out.append({
                    "tone": "danger", "title": "Chômage en hausse rapide",
                    "message": f"Chômage à {now:.1f}% soit {now - low_12m:+.1f} pt au-dessus "
                               "de son plus bas 12 mois — la règle de Sahm (≥ +0.5 pt) signale "
                               "historiquement une entrée en récession.",
                })
        except Exception:
            pass

    return out
