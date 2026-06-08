"""
Global constants — edit here, nowhere else.
"""

SP500_SECTORS = {
    "Technology": 0.30, "Financial Services": 0.13, "Healthcare": 0.12,
    "Consumer Cyclical": 0.10, "Communication Services": 0.09, "Industrials": 0.08,
    "Consumer Defensive": 0.06, "Energy": 0.04, "Utilities": 0.02,
    "Real Estate": 0.02, "Basic Materials": 0.02,
}

# ── Portfolio thresholds ──────────────────────────────────────────────────────
MAX_POSITION_WEIGHT       = 0.25   # alert if single position > 25%
MAX_SECTOR_WEIGHT         = 0.40   # alert if single sector > 40%
ALLOCATION_MIN_SECTOR_PCT = 0.01   # ignore sectors below 1% in diversification score

# ── Simulation ────────────────────────────────────────────────────────────────
MC_SEED              = 42          # fixed seed for reproducible Monte Carlo
MC_N_SIMS            = 500
MC_HORIZON_DAYS      = 252
FRONTIER_N_PORTFOLIOS = 2500       # random portfolios for efficient frontier

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_RISK_FREE  = 4.0           # %
DEFAULT_BENCHMARK  = "SPY"
DEFAULT_PORTFOLIO  = "AAPL, 10\nMSFT, 15\nGOOGL, 20\nSPY, 5\nNVDA, 5"
CACHE_TTL          = 3600          # seconds

# ── Badge rules (metric → [(threshold, label)], None = catch-all) ────────────
BADGE_RULES = {
    "Sharpe":  [(2.0, "🟢 Excellent"), (1.0, "🔵 Bon"), (0.5, "🟡 Moyen"), (None, "🔴 Faible")],
    "Sortino": [(1.5, "🟢 Excellent"), (0.8, "🔵 Bon"),                    (None, "🔴 Faible")],
    "Calmar":  [(1.0, "🟢 Solide"),                                          (None, "🔴 Fragile")],
}

# ── Quality rating score thresholds (0–100) ───────────────────────────────────
QUALITY_HIGH_THRESHOLD    = 65
QUALITY_AVERAGE_THRESHOLD = 40

# ── Piotroski F-Score thresholds ──────────────────────────────────────────────
PIOTROSKI_STRONG  = 7   # ≥7 → strong
PIOTROSKI_NEUTRAL = 4   # 4–6 → neutral, <4 → weak

# ── Shared chart palette ──────────────────────────────────────────────────────
COLORS = {
    "primary":   "#0068C9",
    "secondary": "#83C9FF",
    "success":   "#29a352",
    "warning":   "#e67e00",
    "danger":    "#dc3545",
    "light":     "#5cb85c",
    "bg":        "#ffffff",
    "text":      "#1e293b",
    "grid":      "#e2e8f0",
}

METRIC_EXPLANATIONS = {
    "Sharpe":     "Rendement excédentaire par unité de risque total. Cible ≥ 1.",
    "Sortino":    "Comme le Sharpe, mais pénalise uniquement la volatilité à la baisse.",
    "Calmar":     "CAGR / Max Drawdown. Efficacité face au pire repli subi.",
    "VaR 95%":    "Dans 95 % des séances, la perte ne dépasse pas cette valeur.",
    "CVaR 95%":   "Perte moyenne dans les 5 % pires séances (Expected Shortfall).",
    "Beta":       "Sensibilité aux mouvements du marché. β > 1 = plus volatile.",
    "Alpha":      "Surperformance annuelle vs benchmark après ajustement au risque.",
    "Max DD":     "Plus grande chute depuis un sommet.",
    "CAGR":       "Taux de croissance annuel composé sur la période.",
    "Volatilité": "Écart-type annualisé des rendements journaliers (×√252).",
}
