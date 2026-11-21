from changeguard.models import RiskFeatures
from changeguard.scoring import is_high_risk, score_features


def low() -> RiskFeatures:
    return RiskFeatures(blast_radius_size=1, ci_criticality=2, collision_count=0,
                        freeze_window=False, rollback_present=True, rollback_tested=True,
                        past_failure_rate=0.0, window_risk=0.0, requester_fail_rate=0.0,
                        test_evidence=True)


def high() -> RiskFeatures:
    return RiskFeatures(blast_radius_size=6, ci_criticality=10, collision_count=3,
                        freeze_window=True, rollback_present=False, rollback_tested=False,
                        past_failure_rate=0.8, window_risk=1.0, requester_fail_rate=0.5,
                        test_evidence=False)


def test_lanes():
    assert score_features(low()).lane == "standard"
    a = score_features(high())
    assert a.lane == "reject-back"
    assert a.score <= 100


def test_middle_lane_needs_cab():
    f = low()
    f.collision_count = 3
    f.past_failure_rate = 0.6
    f.window_risk = 0.8
    a = score_features(f)
    assert a.lane == "needs-CAB"
    assert is_high_risk(a) and not is_high_risk(score_features(low()))


def test_drivers_limited_to_three():
    assert len(score_features(high()).drivers) <= 3
