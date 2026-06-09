from analytics.dcf import two_stage_dcf


def test_basic_run():
    out = two_stage_dcf(
        fcf_base=1e9, growth_high=0.10, growth_terminal=0.025,
        wacc=0.09, shares_out=1e8,
    )
    assert "per_share" in out
    assert out["per_share"] > 0


def test_invalid_wacc():
    out = two_stage_dcf(1e9, 0.10, 0.10, 0.09, 1e8)  # wacc <= g_term
    assert "error" in out


def test_zero_shares():
    out = two_stage_dcf(1e9, 0.05, 0.02, 0.08, 0)
    assert "error" in out


def test_explicit_plus_terminal_eq_enterprise():
    out = two_stage_dcf(1e9, 0.08, 0.025, 0.09, 1e8)
    assert abs(out["enterprise"] - (out["npv_explicit"] + out["npv_terminal"])) < 1
