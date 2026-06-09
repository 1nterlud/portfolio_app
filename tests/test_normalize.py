from data.normalize import (
    normalize_debt_to_equity, normalize_dividend_yield,
    normalize_sector, normalize_price, normalize_fcf_yield,
    normalize_stock_info,
)


def test_de_normalises_percent_form():
    assert normalize_debt_to_equity(150) == 1.5


def test_de_passes_through_ratio_form():
    assert normalize_debt_to_equity(0.8) == 0.8


def test_de_none():
    assert normalize_debt_to_equity(None) is None


def test_div_yield_from_rate_price():
    info = {"dividendRate": 2.4, "currentPrice": 100}
    assert abs(normalize_dividend_yield(info) - 0.024) < 1e-9


def test_div_yield_zero_price():
    assert normalize_dividend_yield({"dividendRate": 1, "currentPrice": 0}) is None


def test_div_yield_missing():
    assert normalize_dividend_yield({}) is None


def test_sector_tech_collapse():
    assert normalize_sector("Software—Application") == "Technology"
    assert normalize_sector("Semiconductor Equipment") == "Technology"


def test_sector_passthrough():
    assert normalize_sector("Energy") == "Energy"


def test_sector_none():
    assert normalize_sector(None) == "N/A"


def test_price_fallback_chain():
    assert normalize_price({"regularMarketPreviousClose": 99.5}) == 99.5
    assert normalize_price({"currentPrice": 100, "regularMarketPrice": 101}) == 100


def test_fcf_yield():
    out = normalize_fcf_yield({"freeCashflow": 5e9, "marketCap": 100e9})
    assert abs(out - 0.05) < 1e-9


def test_full_snapshot_minimal():
    snap = normalize_stock_info("AAPL", {"shortName": "Apple", "currentPrice": 200})
    assert snap.ticker == "AAPL"
    assert snap.name   == "Apple"
    assert snap.price  == 200
    assert snap.sector == "N/A"
