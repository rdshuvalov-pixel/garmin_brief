"""Serialize analysis results for JSON storage and LLM context."""

from __future__ import annotations

from typing import Any

from hermes.analysis.signal_scorer import DayStatus, Pattern, ScoreResult


def score_to_dict(result: ScoreResult) -> dict[str, Any]:
    return {
        "day_status": result.day_status.value,
        "alert_count": result.alert_count,
        "watch_count": result.watch_count,
        "top_reasons": result.top_reasons,
        "signals": [_signal_to_dict(s) for s in result.signals],
        "patterns": [_pattern_to_dict(p) for p in result.patterns],
    }


def _signal_to_dict(signal) -> dict[str, Any]:
    return {
        "name": signal.name,
        "level": signal.level.value,
        "reason": signal.reason,
        "value": signal.value,
        "baseline": signal.baseline,
        "delta_pct": signal.delta_pct,
    }


def _pattern_to_dict(pattern: Pattern) -> dict[str, Any]:
    return {
        "name": pattern.name,
        "description": pattern.description,
        "severity": pattern.severity.value,
        "signals_involved": pattern.signals_involved,
    }


STATUS_EMOJI = {
    DayStatus.GREEN: "🟢",
    DayStatus.YELLOW: "🟡",
    DayStatus.RED: "🔴",
    DayStatus.GREY: "⚪",
}

STATUS_LABEL = {
    DayStatus.GREEN: "Green",
    DayStatus.YELLOW: "Yellow",
    DayStatus.RED: "Red",
    DayStatus.GREY: "Grey",
}


def build_llm_context(result: ScoreResult, metrics: dict[str, Any]) -> str:
    lines = [
        f"ДАТА: {result.date}",
        f"СТАТУС ДНЯ: {STATUS_LABEL[result.day_status]}",
        f"АЛЕРТОВ: {result.alert_count}, НАБЛЮДЕНИЙ: {result.watch_count}",
        "",
    ]

    if result.top_reasons:
        lines.append("ГЛАВНЫЕ ПРИЧИНЫ СТАТУСА:")
        for reason in result.top_reasons:
            lines.append(f"  - {reason}")
        lines.append("")

    if result.patterns:
        lines.append("АКТИВНЫЕ ПАТТЕРНЫ:")
        for pattern in result.patterns:
            lines.append(f"  [{pattern.severity.value.upper()}] {pattern.name}: {pattern.description}")
        lines.append("")

    lines.append("МЕТРИКИ:")
    for sig in result.signals:
        marker = {"alert": "❗", "watch": "⚠", "ok": "✓"}.get(sig.level.value, "?")
        val_str = f"{sig.value:.1f}" if sig.value is not None else "—"
        base_str = f"(норма {sig.baseline:.1f})" if sig.baseline is not None else ""
        lines.append(f"  {marker} {sig.name.upper()}: {val_str} {base_str} — {sig.reason}")

    lines.append("")
    lines.extend(_metrics_summary(metrics))
    return "\n".join(lines)


def _metrics_summary(metrics: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    sleep = metrics.get("sleep") or {}
    if sleep.get("duration_minutes") is not None:
        h, m = divmod(int(sleep["duration_minutes"]), 60)
        lines.append(f"СОН: {h}ч {m}м, score={sleep.get('score')}")

    bb = metrics.get("body_battery") or {}
    if bb.get("current") is not None:
        lines.append(f"BODY BATTERY: {bb.get('current')}, charge +{bb.get('overnight_charge')}")

    need = metrics.get("sleep_need") or {}
    if need.get("feedback"):
        lines.append(
            f"SLEEP_NEED: {need.get('feedback')}, baseline {need.get('baseline_minutes')} min, "
            f"actual {need.get('actual_minutes')} min"
        )

    training = metrics.get("training") or {}
    if training.get("readiness") is not None:
        lines.append(f"TRAINING READINESS: {training.get('readiness')}")

    return lines
