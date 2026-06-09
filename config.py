"""
Global constants — edit here, nowhere else.
"""

__version__ = "2.0.0"
APP_NAME    = "Portfolio Pro"

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
FRONTIER_GRID_POINTS  = 60         # convex efficient frontier grid points

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_RISK_FREE  = 4.0           # %
DEFAULT_BENCHMARK  = "SPY"
DEFAULT_PORTFOLIO  = "AAPL, 10\nMSFT, 15\nGOOGL, 20\nSPY, 5\nNVDA, 5"
CACHE_TTL          = 3600          # seconds
PRICE_CACHE_TTL    = 900           # 15 min for live prices
INFO_CACHE_TTL     = 3600          # 1 h for fundamentals

# ── Badge rules (metric → [(threshold, label)], None = catch-all) ────────────
BADGE_RULES = {
    "Sharpe":  [(2.0, "🟢 Excellent"), (1.0, "🔵 Bon"), (0.5, "🟡 Moyen"), (None, "🔴 Faible")],
    "Sortino": [(1.5, "🟢 Excellent"), (0.8, "🔵 Bon"),                    (None, "🔴 Faible")],
    "Calmar":  [(1.0, "🟢 Solide"),                                          (None, "🔴 Fragile")],
}

# ── Quality / Health thresholds (0–100) ──────────────────────────────────────
QUALITY_HIGH_THRESHOLD    = 65
QUALITY_AVERAGE_THRESHOLD = 40
HEALTH_GOOD_THRESHOLD     = 70
HEALTH_AVERAGE_THRESHOLD  = 50

# ── Piotroski F-Score thresholds ──────────────────────────────────────────────
PIOTROSKI_STRONG  = 7   # ≥7 → strong
PIOTROSKI_NEUTRAL = 4   # 4–6 → neutral, <4 → weak

# ── Shared chart palette ──────────────────────────────────────────────────────
COLORS = {
    "primary":   "#2563eb",
    "secondary": "#60a5fa",
    "success":   "#10b981",
    "warning":   "#f59e0b",
    "danger":    "#f43f5e",
    "light":     "#34d399",
    "bg":        "#ffffff",
    "text":      "#0f172a",
    "muted":     "#64748b",
    "grid":      "#e2e8f0",
    "accent":    "#7c3aed",
    "cyan":      "#06b6d4",
    "indigo":    "#4f46e5",
}

# Plotly qualitative palette — used for multi-series charts
CHART_PALETTE = [
    "#2563eb",  # brand
    "#7c3aed",  # violet
    "#06b6d4",  # cyan
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#f43f5e",  # rose
    "#4f46e5",  # indigo
    "#0ea5e9",  # sky
    "#ec4899",  # pink
    "#84cc16",  # lime
]

# Badge tones — used by utils/components.render_badge
BADGE_TONES = {
    "success": {"bg": "#d1fae5", "fg": "#065f46", "border": "#a7f3d0"},
    "info":    {"bg": "#dbeafe", "fg": "#1e40af", "border": "#bfdbfe"},
    "warning": {"bg": "#fef3c7", "fg": "#92400e", "border": "#fde68a"},
    "danger":  {"bg": "#fee2e2", "fg": "#991b1b", "border": "#fecaca"},
    "neutral": {"bg": "#f1f5f9", "fg": "#334155", "border": "#cbd5e1"},
    "violet":  {"bg": "#ede9fe", "fg": "#5b21b6", "border": "#ddd6fe"},
}

# Map legacy color names → tone keys (for back-compat in badges)
LEGACY_BADGE_MAP = {
    "green":  "success",
    "blue":   "info",
    "red":    "danger",
    "orange": "warning",
    "gray":   "neutral",
    "violet": "violet",
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
    "Info Ratio": "Excès de rendement / Tracking Error. Mesure la qualité de l'alpha actif.",
    "Tracking Error": "Écart-type des écarts de rendement vs benchmark, annualisé.",
}

# ── Stress test scenarios (label → (start, end)) ─────────────────────────────
STRESS_SCENARIOS = {
    "Crise 2008":          ("2008-09-01", "2009-03-31"),
    "COVID Crash":         ("2020-02-15", "2020-04-15"),
    "Inflation 2022":      ("2022-01-01", "2022-10-31"),
    "Taper Tantrum 2018":  ("2018-09-15", "2018-12-31"),
}
