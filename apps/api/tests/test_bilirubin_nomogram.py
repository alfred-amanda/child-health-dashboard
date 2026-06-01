
from __future__ import annotations

from app.bilirubin import BilirubinPoint, assess, is_flat_curve, threshold_at, threshold_curve


def test_aap_2022_term_with_hemolytic_risk_published_points() -> None:
    expected = {12: 8.5, 24: 10.5, 48: 14.0, 72: 16.6, 96: 18.2}
    for hour, threshold in expected.items():
        got = threshold_at('39w6d', hour, neurotoxicity_risk=True)
        assert got.status == 'computed'
        assert got.threshold_mg_dl == threshold
        assert got.risk_curve == 'with-risk-factors'


def test_dat_positive_lowers_threshold_vs_no_risk() -> None:
    risk = threshold_at('39w6d', 24, neurotoxicity_risk=True)
    no_risk = threshold_at('39w6d', 24, neurotoxicity_risk=False)
    assert risk.threshold_mg_dl is not None and no_risk.threshold_mg_dl is not None
    assert risk.threshold_mg_dl < no_risk.threshold_mg_dl


def test_curve_is_not_flat_generic_line() -> None:
    curve = threshold_curve('39w6d', neurotoxicity_risk=True)
    assert not is_flat_curve(curve)
    assert len({point['threshold_mg_dl'] for point in curve[:8]}) > 5


def test_uncertain_out_of_range_underclaims_safety() -> None:
    result = threshold_at('39w6d', 4, neurotoxicity_risk=True)
    assert result.status == 'needs_confirmation'
    assert 'not computable' in result.interpretation


def test_thomas_dat_positive_assessment_does_not_reassure_to_defer_care() -> None:
    point = BilirubinPoint(hours=25, bilirubin_mg_dl=5.8, test='TSB', source='SRC-018')
    result = assess(point, '39w6d', dat_positive=True)
    assert result.threshold_mg_dl is not None
    no_risk_threshold = threshold_at('39w6d', 25, neurotoxicity_risk=False).threshold_mg_dl
    assert no_risk_threshold is not None
    assert result.threshold_mg_dl < no_risk_threshold
    assert 'do not use this as reassurance to defer care' in result.interpretation
