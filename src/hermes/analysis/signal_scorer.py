"""Deterministic rule engine for morning metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from hermes.models.metrics import DailySnapshot, SleepNeed


class SignalLevel(str, Enum):
    OK = "ok"
    WATCH = "watch"
    ALERT = "alert"


class DayStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GREY = "grey"


@dataclass
class MetricSignal:
    name: str
    level: SignalLevel
    reason: str
    value: Optional[float] = None
    baseline: Optional[float] = None
    delta_pct: Optional[float] = None


@dataclass
class Pattern:
    name: str
    description: str
    severity: SignalLevel
    signals_involved: list[str]


@dataclass
class ScoreResult:
    date: object
    day_status: DayStatus
    signals: list[MetricSignal] = field(default_factory=list)
    patterns: list[Pattern] = field(default_factory=list)
    alert_count: int = 0
    watch_count: int = 0
    top_reasons: list[str] = field(default_factory=list)


def score_hrv(snap: DailySnapshot) -> Optional[MetricSignal]:
    d = snap.deltas.get("hrv")
    if d is None or d.current is None:
        return None
    if d.baseline_30d is None:
        return MetricSignal(
            "hrv",
            SignalLevel.OK,
            f"HRV {d.current:.0f} ms — база за 30 дней ещё не накоплена",
            d.current,
        )
    pct = d.delta_pct
    if pct is None:
        return None
    if pct <= -20:
        return MetricSignal(
            "hrv",
            SignalLevel.ALERT,
            f"HRV ниже 30-дневной нормы на {abs(pct):.0f}%",
            d.current,
            d.baseline_30d,
            pct,
        )
    if pct <= -10:
        return MetricSignal(
            "hrv",
            SignalLevel.WATCH,
            f"HRV немного ниже нормы ({abs(pct):.0f}%)",
            d.current,
            d.baseline_30d,
            pct,
        )
    return MetricSignal("hrv", SignalLevel.OK, "HRV в норме", d.current, d.baseline_30d, pct)


def score_rhr(snap: DailySnapshot) -> Optional[MetricSignal]:
    d = snap.deltas.get("rhr")
    if d is None or d.current is None:
        return None
    if d.baseline_30d is None:
        return MetricSignal(
            "rhr",
            SignalLevel.OK,
            f"Пульс покоя {d.current:.0f} bpm — база за 30 дней ещё не накоплена",
            d.current,
        )
    delta_bpm = d.delta_abs
    if delta_bpm is None:
        return None
    if delta_bpm >= 8:
        return MetricSignal(
            "rhr",
            SignalLevel.ALERT,
            f"Пульс покоя выше нормы на {delta_bpm:.0f} уд/мин — сильный сигнал перегруза",
            d.current,
            d.baseline_30d,
        )
    if delta_bpm >= 5:
        return MetricSignal(
            "rhr",
            SignalLevel.WATCH,
            f"Пульс покоя выше обычного на {delta_bpm:.0f} уд/мин",
            d.current,
            d.baseline_30d,
        )
    return MetricSignal("rhr", SignalLevel.OK, "Пульс покоя в норме", d.current, d.baseline_30d)


def score_resp(snap: DailySnapshot) -> Optional[MetricSignal]:
    d = snap.deltas.get("resp")
    if d is None or d.current is None or d.baseline_30d is None:
        return None
    pct = d.delta_pct
    if pct is None:
        return None
    if pct >= 10:
        return MetricSignal(
            "resp",
            SignalLevel.ALERT,
            f"Частота дыхания заметно выше нормы (+{pct:.0f}%) — возможный системный стресс",
            d.current,
            d.baseline_30d,
            pct,
        )
    if pct >= 5:
        return MetricSignal(
            "resp",
            SignalLevel.WATCH,
            f"Дыхание немного выше базы (+{pct:.0f}%)",
            d.current,
            d.baseline_30d,
            pct,
        )
    return MetricSignal(
        "resp", SignalLevel.OK, "Частота дыхания стабильна", d.current, d.baseline_30d, pct
    )


def score_temp(snap: DailySnapshot) -> Optional[MetricSignal]:
    raw = snap.raw
    if raw.temp_deviation_c is None:
        return None
    dev = raw.temp_deviation_c
    if dev >= 0.5:
        return MetricSignal(
            "temp",
            SignalLevel.ALERT,
            f"Температура выше нормы на {dev:+.1f}°C — снизить нагрузку, следить за симптомами",
            dev,
        )
    if dev >= 0.3:
        return MetricSignal(
            "temp",
            SignalLevel.WATCH,
            f"Небольшое повышение температуры ({dev:+.1f}°C)",
            dev,
        )
    return MetricSignal("temp", SignalLevel.OK, "Температура в норме", dev)


def score_spo2(snap: DailySnapshot) -> Optional[MetricSignal]:
    raw = snap.raw
    avg = raw.spo2_avg_pct
    min_val = raw.spo2_min_pct
    if avg is None:
        return None
    if avg < 94:
        return MetricSignal(
            "spo2",
            SignalLevel.ALERT,
            f"SpO₂ низкий (ср. {avg:.0f}%) — повторяющиеся провалы требуют внимания",
            avg,
        )
    if min_val is not None and min_val < 90:
        return MetricSignal(
            "spo2",
            SignalLevel.WATCH,
            f"SpO₂: минимум ночью {min_val:.0f}% (ср. {avg:.0f}%)",
            avg,
        )
    if avg < 96:
        return MetricSignal(
            "spo2",
            SignalLevel.WATCH,
            f"SpO₂ немного ниже нормы (ср. {avg:.0f}%)",
            avg,
        )
    return MetricSignal("spo2", SignalLevel.OK, f"SpO₂ в норме ({avg:.0f}%)", avg)


def score_sleep(snap: DailySnapshot) -> Optional[MetricSignal]:
    d = snap.deltas.get("sleep")
    if d is None or d.current is None:
        return None
    if d.baseline_30d is None:
        return MetricSignal(
            "sleep",
            SignalLevel.OK,
            f"Сон {d.current:.1f}ч — база за 30 дней ещё не накоплена",
            d.current,
        )
    deficit_h = d.baseline_30d - d.current
    if deficit_h >= 1.5:
        return MetricSignal(
            "sleep",
            SignalLevel.ALERT,
            f"Сон на {deficit_h:.1f}ч короче нормы ({d.current:.1f}ч vs {d.baseline_30d:.1f}ч обычно)",
            d.current,
            d.baseline_30d,
        )
    if deficit_h >= 0.75:
        return MetricSignal(
            "sleep",
            SignalLevel.WATCH,
            f"Сон немного короче нормы ({d.current:.1f}ч vs {d.baseline_30d:.1f}ч)",
            d.current,
            d.baseline_30d,
        )
    return MetricSignal(
        "sleep", SignalLevel.OK, f"Продолжительность сна в норме ({d.current:.1f}ч)", d.current
    )


def score_deep(snap: DailySnapshot) -> Optional[MetricSignal]:
    d = snap.deltas.get("deep")
    if d is None or d.current is None or d.baseline_30d is None:
        return None
    pct = d.delta_pct
    if pct is None:
        return None
    if pct <= -30:
        return MetricSignal(
            "deep",
            SignalLevel.ALERT,
            f"Глубокого сна значительно меньше нормы ({abs(pct):.0f}%) — физическое восстановление неполное",
            d.current,
            d.baseline_30d,
            pct,
        )
    if pct <= -15:
        return MetricSignal(
            "deep",
            SignalLevel.WATCH,
            f"Глубокого сна меньше обычного ({abs(pct):.0f}%)",
            d.current,
            d.baseline_30d,
            pct,
        )
    return MetricSignal("deep", SignalLevel.OK, "Глубокий сон в норме", d.current)


def score_rem(snap: DailySnapshot) -> Optional[MetricSignal]:
    d = snap.deltas.get("rem")
    if d is None or d.current is None or d.baseline_30d is None:
        return None
    pct = d.delta_pct
    if pct is None:
        return None
    if pct <= -25:
        return MetricSignal(
            "rem",
            SignalLevel.ALERT,
            f"REM-сон значительно ниже нормы ({abs(pct):.0f}%) — когнитивное восстановление снижено",
            d.current,
            d.baseline_30d,
            pct,
        )
    if pct <= -15:
        return MetricSignal(
            "rem",
            SignalLevel.WATCH,
            f"REM-сон немного ниже обычного ({abs(pct):.0f}%)",
            d.current,
            d.baseline_30d,
            pct,
        )
    return MetricSignal("rem", SignalLevel.OK, "REM-сон в норме", d.current)


def score_sleep_need(snap: DailySnapshot) -> Optional[MetricSignal]:
    need: SleepNeed | None = snap.sleep_need
    if need is None or need.feedback is None:
        return None

    feedback = need.feedback.upper()
    actual = need.actual_minutes
    baseline = need.baseline_minutes
    deficit = need.deficit_minutes

    if feedback in ("HIGHLY_INCREASED", "INCREASED"):
        detail = ""
        if deficit and deficit > 0:
            detail = f" — дефицит ~{deficit // 60}ч {deficit % 60}м"
        return MetricSignal(
            "sleep_need",
            SignalLevel.ALERT if feedback == "HIGHLY_INCREASED" else SignalLevel.WATCH,
            f"Garmin sleep need: {feedback}{detail} (нужно {actual} мин, база {baseline} мин)",
            float(actual or 0),
            float(baseline) if baseline else None,
        )
    if feedback.startswith("NO_CHANGE"):
        return MetricSignal(
            "sleep_need",
            SignalLevel.OK,
            "Потребность во сне в норме",
            float(actual or 0),
            float(baseline) if baseline else None,
        )
    return MetricSignal(
        "sleep_need",
        SignalLevel.WATCH,
        f"Garmin sleep need: {feedback}",
        float(actual or 0),
        float(baseline) if baseline else None,
    )


def detect_patterns(signals: dict[str, MetricSignal], snap: DailySnapshot) -> list[Pattern]:
    patterns: list[Pattern] = []

    def level(name: str) -> Optional[SignalLevel]:
        sig = signals.get(name)
        return sig.level if sig else None

    def is_alert(name: str) -> bool:
        return level(name) == SignalLevel.ALERT

    def is_watch_or_alert(name: str) -> bool:
        return level(name) in (SignalLevel.WATCH, SignalLevel.ALERT)

    if (
        is_watch_or_alert("sleep_need")
        and is_watch_or_alert("sleep")
        and not is_alert("hrv")
    ):
        patterns.append(
            Pattern(
                name="SLEEP_DEBT_MASKED",
                description=(
                    "Garmin указывает на накопленную потребность во сне — HRV ещё держится, "
                    "но организм работает в кредит. Это не зелёный день."
                ),
                severity=SignalLevel.ALERT,
                signals_involved=["sleep_need", "sleep", "hrv"],
            )
        )

    alert_physio = sum(1 for m in ["rhr", "resp", "temp"] if is_watch_or_alert(m))
    if alert_physio >= 2 and is_watch_or_alert("hrv"):
        patterns.append(
            Pattern(
                name="SYSTEMIC_STRESS",
                description=(
                    "Несколько физиологических сигналов одновременно выше нормы — "
                    "паттерн системного стресса или сильного перегруза."
                ),
                severity=SignalLevel.ALERT,
                signals_involved=[
                    m for m in ["rhr", "resp", "temp", "hrv"] if is_watch_or_alert(m)
                ],
            )
        )

    if is_watch_or_alert("temp") and is_watch_or_alert("rhr") and is_watch_or_alert("resp"):
        patterns.append(
            Pattern(
                name="POSSIBLE_ILLNESS",
                description=(
                    "Паттерн похож на начало болезни или сильный системный стресс: "
                    "температура, пульс и дыхание одновременно выше нормы."
                ),
                severity=SignalLevel.ALERT,
                signals_involved=["temp", "rhr", "resp"],
            )
        )

    if is_watch_or_alert("rem") and is_watch_or_alert("sleep_need"):
        patterns.append(
            Pattern(
                name="COGNITIVE_DRAIN",
                description=(
                    "REM-сон ниже нормы на фоне повышенной потребности во сне — "
                    "когнитивные ресурсы снижены."
                ),
                severity=SignalLevel.WATCH,
                signals_involved=["rem", "sleep_need"],
            )
        )

    if is_watch_or_alert("deep") and is_watch_or_alert("hrv"):
        patterns.append(
            Pattern(
                name="PHYSICAL_UNDERRECOVERY",
                description=(
                    "Глубокий сон и HRV оба ниже нормы — физическое восстановление неполное."
                ),
                severity=SignalLevel.WATCH,
                signals_involved=["deep", "hrv"],
            )
        )

    return patterns


def classify_day(signals: dict[str, MetricSignal], patterns: list[Pattern]) -> DayStatus:
    alert_count = sum(1 for s in signals.values() if s.level == SignalLevel.ALERT)
    watch_count = sum(1 for s in signals.values() if s.level == SignalLevel.WATCH)
    critical_patterns = [p for p in patterns if p.severity == SignalLevel.ALERT]

    core_present = sum(1 for k in ["hrv", "rhr", "sleep"] if signals.get(k) is not None)
    if core_present < 2:
        return DayStatus.GREY

    if alert_count >= 3 or (alert_count >= 2 and len(critical_patterns) >= 1):
        return DayStatus.RED

    if any(p.name in ("POSSIBLE_ILLNESS", "SYSTEMIC_STRESS") for p in patterns):
        return DayStatus.RED

    if alert_count >= 1 or watch_count >= 2 or len(patterns) >= 1:
        return DayStatus.YELLOW

    return DayStatus.GREEN


def score(snap: DailySnapshot) -> ScoreResult:
    if snap.data_quality == "grey" or snap.force_grey:
        return ScoreResult(
            date=snap.raw.date,
            day_status=DayStatus.GREY,
            top_reasons=["Данные неполные или ненадёжные — выводы по этой ночи делать не стоит"],
        )

    scorers = [
        score_hrv,
        score_rhr,
        score_resp,
        score_temp,
        score_spo2,
        score_sleep,
        score_sleep_need,
        score_deep,
        score_rem,
    ]
    signal_list = [fn(snap) for fn in scorers]
    signal_list = [s for s in signal_list if s is not None]
    signals_dict = {s.name: s for s in signal_list}

    patterns = detect_patterns(signals_dict, snap)
    day_status = classify_day(signals_dict, patterns)

    reasons: list[str] = []
    for p in patterns[:2]:
        reasons.append(p.description)
    for s in signal_list:
        if s.level == SignalLevel.ALERT and s.name not in {
            n for p in patterns for n in p.signals_involved
        }:
            reasons.append(s.reason)
    for s in signal_list:
        if s.level == SignalLevel.WATCH and len(reasons) < 3:
            reasons.append(s.reason)

    return ScoreResult(
        date=snap.raw.date,
        day_status=day_status,
        signals=signal_list,
        patterns=patterns,
        alert_count=sum(1 for s in signal_list if s.level == SignalLevel.ALERT),
        watch_count=sum(1 for s in signal_list if s.level == SignalLevel.WATCH),
        top_reasons=reasons[:3],
    )
