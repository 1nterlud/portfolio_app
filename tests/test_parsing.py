from utils.parsing import parse_positions


def test_basic_two_field():
    df = parse_positions("AAPL, 10\nMSFT, 5")
    assert len(df) == 2
    assert list(df["Symbol"]) == ["AAPL", "MSFT"]
    assert list(df["Qty"])    == [10, 5]
    assert df["CostBasis"].isna().all()


def test_three_field_with_cost_basis():
    df = parse_positions("AAPL, 10, 150.5\nMSFT, 5, 280")
    assert df.loc[0, "CostBasis"] == 150.5
    assert df.loc[1, "CostBasis"] == 280.0


def test_skips_invalid_lines():
    df = parse_positions("AAPL, 10\nGARBAGE\n,5\nMSFT, -3\nNVDA, 2")
    assert list(df["Symbol"]) == ["AAPL", "NVDA"]


def test_uppercases_tickers():
    df = parse_positions("aapl, 1")
    assert df.loc[0, "Symbol"] == "AAPL"
