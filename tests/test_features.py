from conftest import cr

from changeguard.features import (
    build_features,
    collision_count,
    in_freeze,
    past_failure_rate,
    requester_fail_rate,
    window_risk,
)
from changeguard.models import ChangeRequest


def test_blast_radius_orders_db(history):
    f = build_features(cr(), history)
    assert f.blast_radius_size == 6  # orders-db + 5 dependents
    assert f.ci_criticality == 10


def test_freeze_flag():
    assert in_freeze(ChangeRequest.model_validate(
        {**cr().model_dump(), "scheduled_at": "2024-12-25T10:00:00"}).scheduled_at)
    assert not in_freeze(cr().scheduled_at)


def test_window_risk_offhours_weekend():
    assert window_risk(cr(scheduled_at="2025-03-16T23:00:00").scheduled_at) == 1.0
    assert window_risk(cr(scheduled_at="2025-03-12T10:00:00").scheduled_at) == 0.0


def test_collision_count(history):
    c = cr(scheduled_at="2025-01-02T11:00:00")
    assert collision_count(c, history) >= 1


def test_past_failure_and_requester_rates(history):
    assert 0.0 <= past_failure_rate(cr(), history) <= 1.0
    assert requester_fail_rate(cr(requester="nobody-new"), history) == 0.0


def test_unknown_ci_fail_closed(history):
    f = build_features(cr(ci="ghost-ci-99"), history)
    assert f.ci_criticality == 10
