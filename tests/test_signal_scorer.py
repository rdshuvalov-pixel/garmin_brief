"""Tests for deterministic morning scoring."""

from datetime import date

from hermes.analysis.signal_scorer import SignalLevel, score_hrv
from hermes.models.metrics import Baseline, DailySnapshot, MetricDelta, RawMetrics


def test_score_hrv_alert_when_below_baseline():
    snap = DailySnapshot(
        raw=RawMetrics(date=date(2026, 5, 24), hrv_ms=40.0),
        baseline=Baseline(hrv_30d=50.0),
        deltas={
            "hrv": MetricDelta("hrv", 40.0, 50.0).compute(),
        },
    )
    signal = score_hrv(snap)
    assert signal is not None
    assert signal.level == SignalLevel.ALERT
    assert signal.delta_pct == -20.0


def test_score_hrv_ok_when_at_baseline():
    snap = DailySnapshot(
        raw=RawMetrics(date=date(2026, 5, 24), hrv_ms=50.0),
        baseline=Baseline(hrv_30d=50.0),
        deltas={
            "hrv": MetricDelta("hrv", 50.0, 50.0).compute(),
        },
    )
    signal = score_hrv(snap)
    assert signal is not None
    assert signal.level == SignalLevel.OK
