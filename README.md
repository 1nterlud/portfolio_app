# Portfolio Pro

Application web d'analyse de portefeuille boursier — Streamlit, 100 % données gratuites.

> ⚠️ **Disclaimer** : outil pédagogique uniquement. Rien dans cette application ne
> constitue un conseil en investissement.

## Fonctionnalités

**Portfolio Dashboard** — analyse complète d'un portefeuille saisi en texte ou CSV :
- Allocation par ticker et par secteur (vs poids S&P 500)
- Métriques : CAGR, Sharpe, Sortino, Calmar, volatilité, VaR/CVaR 95 %, max drawdown
- MPT vs benchmark : alpha, bêta, information ratio, tracking error
- Simulation Monte Carlo (500 trajectoires, distribution normale ou Student-t)
- Frontière efficiente (Markowitz/SLSQP), portefeuilles max-Sharpe et min-volatilité
- Métriques glissantes, stress tests historiques (2008, COVID, inflation 2022, 2018)
- Backtest allocation actuelle vs allocation cible
- Données macro FRED (taux directeur, CPI, 10 ans US, chômage, VIX) — *optionnel*
- Health Score 0-100, résumé exécutif, alertes de concentration, export PDF

**Stock Research** — analyse d'un titre : valorisation, qualité (Piotroski F-Score),
résultats financiers, analystes, news, insiders, simulateur DCF deux étapes, et
indicateurs techniques (RSI, MACD, Bollinger) **calculés localement** — aucune clé requise.

**Compare Stocks** — comparaison côte à côte de 2 à 4 tickers.

**Watchlist** — suivi de prix avec sparklines 30 jours.

## Installation

```bash
git clone https://github.com/1nterlud/portfolio_app.git
cd portfolio_app
pip install -r requirements.txt
streamlit run app.py
```

Python 3.11+ recommandé.

## Tests

```bash
pytest tests/ -q
```

## Sources de données (gratuites)

| Source | Usage | Clé requise |
|---|---|---|
| [yfinance](https://github.com/ranaroussi/yfinance) | Prix, fondamentaux, news, insiders | Non |
| [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) | Macro US (tab 🌍 Macro) | Oui — gratuite, **optionnelle** |

L'application fonctionne intégralement sans aucune clé API ; seul le tab Macro
affiche alors un message d'information.

### Configurer la clé FRED (optionnel)

Local — créer `.streamlit/secrets.toml` (gitignored) :

```toml
FRED_API_KEY = "votre-clé"
```

Streamlit Cloud — App settings → Secrets, même contenu.

## Limites des données

- yfinance : cours quotidiens uniquement (pas d'intraday), différés ~15 min,
  champs fondamentaux parfois manquants selon le ticker.
- Devise : les valeurs sont affichées dans la devise de cotation du ticker
  (USD pour les tickers US) — pas de conversion multi-devises.
- Les caches internes sont de 15 min (prix) et 1 h (fondamentaux, macro) ;
  bouton 🔄 dans la sidebar pour forcer le rechargement.

## Architecture

```
analytics/   calculs purs (métriques, optimisation, Monte Carlo, DCF, technique…)
data/        fetching + normalisation (yfinance, FRED) avec cache Streamlit
ui/          rendu Streamlit (une page ou un tab par module)
utils/       parsing, formatting, PDF, profils, composants HTML
config.py    toutes les constantes
tests/       pytest (analytics + parsing)
```

Convention : aucune logique financière dans `ui/`, aucun import Streamlit dans `analytics/`.

## Déploiement Streamlit Cloud

L'app est compatible Streamlit Cloud sans configuration particulière :
le CSS et les chemins sont résolus quel que soit le working directory, et
aucun secret n'est requis pour démarrer.
