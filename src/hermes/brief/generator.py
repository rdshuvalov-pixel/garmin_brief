"""Short Telegram brief from ScoreResult (no LLM)."""

from __future__ import annotations

from hermes.analysis.signal_scorer import DayStatus, ScoreResult
from hermes.brief.serialize import STATUS_EMOJI, STATUS_LABEL

MAX_TELEGRAM_LENGTH = 700

_PLAN = {
    DayStatus.GREEN: "Можно планировать обычную нагрузку и умеренные тренировки.",
    DayStatus.YELLOW: "Сегодня умеренный режим, без HIIT и перегруза встречами.",
    DayStatus.RED: "Приоритет — отдых и сон, интенсивную нагрузку отменить.",
    DayStatus.GREY: "Данные неполные — ориентируйся на самочувствие.",
}


def generate_telegram_brief(result: ScoreResult, *, brief_url: str = "") -> str:
    emoji = STATUS_EMOJI[result.day_status]
    label = STATUS_LABEL[result.day_status]

    if result.top_reasons:
        reason = result.top_reasons[0]
    elif result.day_status == DayStatus.GREY:
        reason = "данные Garmin неполные"
    else:
        reason = "показатели в пределах нормы"

    lines = [f"{emoji} {label}. {reason}.", "", _PLAN[result.day_status]]
    if brief_url:
        lines.extend(["", f"Полный бриф: {brief_url}"])

    text = "\n".join(lines)
    if len(text) > MAX_TELEGRAM_LENGTH:
        text = text[: MAX_TELEGRAM_LENGTH - 3].rstrip() + "..."
    return text
