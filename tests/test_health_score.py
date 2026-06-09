from analytics.health_score import calc_health_score


def _m(**overrides):
    base = {"sharpe": 1.0, "max_dd": -0.10, "calmar": 1.0}
    base.update(overrides)
    return base


def _mpt(alpha_ann=0.02):
    return {"alpha_ann": alpha_ann, "beta": 1.0, "r_val": 0.9}


def _div(score=75):
    return {"score": score, "label": "Bien diversifié", "color": "green"}


def test_high_quality_portfolio():
    out = calc_health_score(_m(sharpe=2.0, max_dd=-0.10),
                            _mpt(alpha_ann=0.05), _div(score=80))
    assert out["score"] >= 75
    assert out["label"] == "Excellent"


def test_weak_portfolio():
    out = calc_health_score(_m(sharpe=0.1, max_dd=-0.45),
                            _mpt(alpha_ann=-0.05), _div(score=20))
    assert out["score"] < 50
    assert out["label"] == "À surveiller"


def test_breakdown_keys():
    out = calc_health_score(_m(), _mpt(), _div())
    assert set(out["breakdown"]) == {"Sharpe", "Drawdown", "Diversification", "Alpha"}


def test_no_mpt_safe():
    out = calc_health_score(_m(), None, _div())
    assert 0 <= out["score"] <= 100
