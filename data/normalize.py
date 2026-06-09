"""
Centralized field normalization for yfinance's inconsistent outputs.
Every callsite should consume normalized info — never raw yfinance dicts.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from utils.logging_setup import get_logger

log = get_logger("normalize")

_TECH_KEYWORDS = ("Technology", "Software", "Hardware", "Semiconductor", "Internet")


def normalize_debt_to_equity(de_raw) -> float | None:
    """yfinance returns D/E as ratio (0.5) OR as percent (50). Detect & normalize to ratio."""
    if de_raw is None:
        return None
    try:
        de = float(de_raw)
        return de / 100 if de > 10 else de
    except (TypeError, ValueError):
        return None


def normalize_dividend_yield(info: dict) -> float | None:
    """Compute yield from dividendRate / price — bypasses yfinance's inconsistent dividendYield."""
    rate  = info.get("dividendRate")
    price = info.get("currentPrice") or info.get("regularMarketPreviousClose")
    if rate and price:
        try:
            p = float(price)
            if p > 0:
                return float(rate) / p
        except (TypeError, ValueError):
            return None
    return None


def normalize_sector(sec_raw: str | None) -> str:
    """Collapse tech sub-sectors into a single 'Technology' bucket."""
    if not sec_raw:
        return "N/A"
    if any(kw in sec_raw for kw in _TECH_KEYWORDS):
        return "Technology"
    return sec_raw


def normalize_price(info: dict) -> float | None:
    """Best-effort current price with multiple fallbacks."""
    for k in ("currentPrice", "regularMarketPrice", "regularMarketPreviousClose", "previousClose"):
        v = info.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def normalize_fcf_yield(info: dict) -> float | None:
    fcf  = info.get("freeCashflow")
    mcap = info.get("marketCap")
    if fcf is not None and mcap and mcap > 0:
        try:
            return float(fcf) / float(mcap)
        except (TypeError, ValueError):
            return None
    return None


@dataclass
class StockSnapshot:
    """Normalized view of yfinance info — every field already clean."""
    ticker:      str
    name:        str
    sector:      str
    industry:    str
    exchange:    str
    price:       float | None
    market_cap:  float | None
    enterprise_value: float | None
    # Valuation
    pe_trailing: float | None
    pe_forward:  float | None
    price_book:  float | None
    peg:         float | None
    ev_ebitda:   float | None
    ev_revenue:  float | None
    fcf_yield:   float | None
    # Profitability
    profit_margin:    float | None
    operating_margin: float | None
    gross_margin:     float | None
    roe:              float | None
    roa:              float | None
    revenue_growth:   float | None
    earnings_growth:  float | None
    # Balance / risk
    debt_to_equity:   float | None
    current_ratio:    float | None
    quick_ratio:      float | None
    total_debt:       float | None
    total_cash:       float | None
    beta:             float | None
    short_pct_float:  float | None
    # Income / dividends
    div_yield:        float | None
    div_rate:         float | None
    payout_ratio:     float | None
    ex_div_date:      str | None
    # Analysts
    target_mean:  float | None
    target_low:   float | None
    target_high:  float | None
    n_analysts:   int | None
    recommendation: str
    # Extras
    summary:    str
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return self.__dict__


def normalize_stock_info(ticker: str, info: dict) -> StockSnapshot:
    """Build a StockSnapshot from a raw yfinance info dict."""
    if not info:
        log.warning(f"empty info for {ticker}")
    return StockSnapshot(
        ticker      = ticker,
        name        = info.get("longName") or info.get("shortName") or ticker,
        sector      = normalize_sector(info.get("sector")),
        industry    = info.get("industry") or "N/A",
        exchange    = info.get("exchange") or "",
        price       = normalize_price(info),
        market_cap  = info.get("marketCap"),
        enterprise_value = info.get("enterpriseValue"),
        pe_trailing = info.get("trailingPE"),
        pe_forward  = info.get("forwardPE"),
        price_book  = info.get("priceToBook"),
        peg         = info.get("pegRatio") or info.get("trailingPegRatio"),
        ev_ebitda   = info.get("enterpriseToEbitda"),
        ev_revenue  = info.get("enterpriseToRevenue"),
        fcf_yield   = normalize_fcf_yield(info),
        profit_margin    = info.get("profitMargins"),
        operating_margin = info.get("operatingMargins"),
        gross_margin     = info.get("grossMargins"),
        roe              = info.get("returnOnEquity"),
        roa              = info.get("returnOnAssets"),
        revenue_growth   = info.get("revenueGrowth"),
        earnings_growth  = info.get("earningsGrowth"),
        debt_to_equity   = normalize_debt_to_equity(info.get("debtToEquity")),
        current_ratio    = info.get("currentRatio"),
        quick_ratio      = info.get("quickRatio"),
        total_debt       = info.get("totalDebt"),
        total_cash       = info.get("totalCash"),
        beta             = info.get("beta"),
        short_pct_float  = info.get("shortPercentOfFloat"),
        div_yield        = normalize_dividend_yield(info),
        div_rate         = info.get("dividendRate"),
        payout_ratio     = info.get("payoutRatio"),
        ex_div_date      = str(info.get("exDividendDate")) if info.get("exDividendDate") else None,
        target_mean      = info.get("targetMeanPrice"),
        target_low       = info.get("targetLowPrice"),
        target_high      = info.get("targetHighPrice"),
        n_analysts       = info.get("numberOfAnalystOpinions"),
        recommendation   = (info.get("recommendationKey") or "").replace("_", " ").title(),
        summary          = info.get("longBusinessSummary") or "",
    )
