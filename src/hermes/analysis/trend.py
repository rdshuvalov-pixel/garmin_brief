"""Rolling baselines and per-metric deltas from history."""

from __future__ import annotations

import statistics
from typing import Optional

from hermes.models.metrics import Baseline, DailySnapshot, MetricDelta, RawMetrics, SleepNeed


def _median(values: list[float]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(statistics.median(clean), 2)


def compute_baseline(history: list[RawMetrics]) -> Baseline:
    h7 = history[-7:] if len(history) >= 7 else history
    h30 = history

    return Baseline(
        hrv_7d=_median([r.hrv_ms for r in h7 if r.hrv_ms is not None]),
        hrv_30d=_median([r.hrv_ms for r in h30 if r.hrv_ms is not None]),
        rhr_7d=_median([r.resting_hr_bpm for r in h7 if r.resting_hr_bpm is not None]),
        rhr_30d=_median([r.resting_hr_bpm for r in h30 if r.resting_hr_bpm is not None]),
        resp_7d=_median([r.respiratory_rate for r in h7 if r.respiratory_rate is not None]),
        resp_30d=_median([r.respiratory_rate for r in h30 if r.respiratory_rate is not None]),
        sleep_7d=_median([r.total_sleep_hours for r in h7 if r.total_sleep_hours is not None]),
        sleep_30d=_median([r.total_sleep_hours for r in h30 if r.total_sleep_hours is not None]),
        deep_7d=_median([r.deep_sleep_hours for r in h7 if r.deep_sleep_hours is not None]),
        deep_30d=_median([r.deep_sleep_hours for r in h30 if r.deep_sleep_hours is not None]),
        rem_7d=_median([r.rem_sleep_hours for r in h7 if r.rem_sleep_hours is not None]),
        rem_30d=_median([r.rem_sleep_hours for r in h30 if r.rem_sleep_hours is not None]),
    )


def compute_deltas(raw: RawMetrics, baseline: Baseline) -> dict[str, MetricDelta]:
    pairs = [
        ("hrv", raw.hrv_ms, baseline.hrv_30d),
        ("rhr", raw.resting_hr_bpm, baseline.rhr_30d),
        ("resp", raw.respiratory_rate, baseline.resp_30d),
        ("sleep", raw.total_sleep_hours, baseline.sleep_30d),
        ("deep", raw.deep_sleep_hours, baseline.deep_30d),
        ("rem", raw.rem_sleep_hours, baseline.rem_30d),
    ]
    deltas: dict[str, MetricDelta] = {}
    for name, current, base in pairs:
        deltas[name] = MetricDelta(name=name, current=current, baseline_30d=base).compute()

    deltas["spo2"] = MetricDelta(
        name="spo2", current=raw.spo2_avg_pct, baseline_30d=None
    )
    deltas["temp"] = MetricDelta(
        name="temp",
        current=raw.temp_deviation_c,
        baseline_30d=0.0,
        delta_abs=raw.temp_deviation_c,
        delta_pct=None,
    )
    return deltas


def build_snapshot(
    raw: RawMetrics,
    history_30d: list[RawMetrics],
    *,
    sleep_need: SleepNeed | None = None,
    force_grey: bool = False,
) -> DailySnapshot:
    baseline = compute_baseline(history_30d)
    deltas = compute_deltas(raw, baseline)
    snapshot = DailySnapshot(
        raw=raw,
        baseline=baseline,
        sleep_need=sleep_need,
        deltas=deltas,
        force_grey=force_grey,
    )
    snapshot.label_quality()
    return snapshot
