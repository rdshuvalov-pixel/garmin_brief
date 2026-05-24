"""Typed data models for Garmin morning metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class RawMetrics:
    """Raw values for a single morning snapshot."""

    date: date

    hrv_ms: Optional[float] = None
    resting_hr_bpm: Optional[float] = None
    respiratory_rate: Optional[float] = None
    temp_deviation_c: Optional[float] = None
    spo2_avg_pct: Optional[float] = None
    spo2_min_pct: Optional[float] = None
    total_sleep_seconds: Optional[int] = None
    deep_sleep_seconds: Optional[int] = None
    rem_sleep_seconds: Optional[int] = None

    @property
    def total_sleep_hours(self) -> Optional[float]:
        if self.total_sleep_seconds is None:
            return None
        return round(self.total_sleep_seconds / 3600, 2)

    @property
    def deep_sleep_hours(self) -> Optional[float]:
        if self.deep_sleep_seconds is None:
            return None
        return round(self.deep_sleep_seconds / 3600, 2)

    @property
    def rem_sleep_hours(self) -> Optional[float]:
        if self.rem_sleep_seconds is None:
            return None
        return round(self.rem_sleep_seconds / 3600, 2)

    def available_fields(self) -> list[str]:
        fields = [
            "hrv_ms",
            "resting_hr_bpm",
            "respiratory_rate",
            "temp_deviation_c",
            "spo2_avg_pct",
            "spo2_min_pct",
            "total_sleep_seconds",
            "deep_sleep_seconds",
            "rem_sleep_seconds",
        ]
        return [name for name in fields if getattr(self, name) is not None]

    def is_usable(self) -> bool:
        return all(
            [
                self.hrv_ms is not None,
                self.resting_hr_bpm is not None,
                self.total_sleep_seconds is not None,
            ]
        )


@dataclass
class SleepNeed:
    """Garmin sleepNeed from dailySleepDTO."""

    baseline_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    feedback: Optional[str] = None
    deficit_minutes: Optional[int] = None


@dataclass
class Baseline:
    hrv_7d: Optional[float] = None
    hrv_30d: Optional[float] = None
    rhr_7d: Optional[float] = None
    rhr_30d: Optional[float] = None
    resp_7d: Optional[float] = None
    resp_30d: Optional[float] = None
    sleep_7d: Optional[float] = None
    sleep_30d: Optional[float] = None
    deep_7d: Optional[float] = None
    deep_30d: Optional[float] = None
    rem_7d: Optional[float] = None
    rem_30d: Optional[float] = None


@dataclass
class MetricDelta:
    name: str
    current: Optional[float]
    baseline_30d: Optional[float]
    delta_abs: Optional[float] = None
    delta_pct: Optional[float] = None

    def compute(self) -> MetricDelta:
        if (
            self.current is not None
            and self.baseline_30d is not None
            and self.baseline_30d != 0
        ):
            self.delta_abs = round(self.current - self.baseline_30d, 2)
            self.delta_pct = round(
                (self.current - self.baseline_30d) / self.baseline_30d * 100, 1
            )
        return self


@dataclass
class DailySnapshot:
    raw: RawMetrics
    baseline: Baseline
    sleep_need: Optional[SleepNeed] = None
    deltas: dict[str, MetricDelta] = field(default_factory=dict)
    data_quality: str = "full"
    force_grey: bool = False

    def label_quality(self) -> None:
        if self.force_grey:
            self.data_quality = "grey"
            return
        available = len(self.raw.available_fields())
        if available >= 7:
            self.data_quality = "full"
        elif available >= 4 and self.raw.is_usable():
            self.data_quality = "partial"
        else:
            self.data_quality = "grey"
