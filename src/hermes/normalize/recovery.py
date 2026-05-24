"""Normalize Garmin raw data into unified recovery schema."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from hermes.models.metrics import RawMetrics, SleepNeed


def normalize_recovery(raw: dict[str, Any], date: str) -> dict[str, Any]:
    sleep_raw = raw.get("sleep")
    stats_raw = raw.get("stats")
    hr_raw = raw.get("heart_rate")
    stress_raw = raw.get("stress")
    bb_raw = raw.get("body_battery")
    hrv_raw = raw.get("hrv")
    training_raw = raw.get("training_readiness")

    sleep = _normalize_sleep(sleep_raw)
    sleep_need = _normalize_sleep_need(sleep_raw)
    body_battery = _normalize_body_battery(bb_raw, stats_raw)
    stress = _normalize_stress(stress_raw)
    heart_rate = _normalize_heart_rate(hr_raw, stats_raw)
    hrv = _normalize_hrv(hrv_raw)
    training = _normalize_training(training_raw)
    respiration = _normalize_respiration(raw.get("respiration"))
    spo2 = _normalize_spo2(raw.get("spo2"), sleep_raw)
    temp = _normalize_temp(raw.get("skin_temp"))

    if sleep and sleep_raw and isinstance(sleep_raw, dict):
        dto = sleep_raw.get("dailySleepDTO") or {}
        if isinstance(dto, dict):
            if dto.get("deepSleepSeconds") is not None:
                sleep["deep_minutes"] = int(dto["deepSleepSeconds"] // 60)
            if dto.get("remSleepSeconds") is not None:
                sleep["rem_minutes"] = int(dto["remSleepSeconds"] // 60)

    return {
        "date": date,
        "source": "garmin_connect",
        "sleep": sleep,
        "sleep_need": sleep_need,
        "body_battery": body_battery,
        "stress": stress,
        "heart_rate": heart_rate,
        "hrv": hrv,
        "training": training,
        "respiration": respiration,
        "spo2": spo2,
        "temp": temp,
        "raw_available": {
            "sleep": sleep is not None,
            "body_battery": body_battery is not None,
            "stress": stress is not None,
            "heart_rate": heart_rate is not None,
            "hrv": hrv is not None,
            "training_readiness": training is not None,
            "respiration": respiration is not None,
            "spo2": spo2 is not None,
            "temp": temp is not None,
        },
    }


def _is_error_payload(data: Any) -> bool:
    return (
        not data
        or not isinstance(data, dict)
        or data.get("_error") is not None
        or data.get("_empty") is not None
    )


def _normalize_sleep(data: Any) -> dict[str, Any] | None:
    if _is_error_payload(data):
        return None

    dto = data.get("dailySleepDTO") if isinstance(data, dict) else None
    if not dto or not isinstance(dto, dict):
        dto = data if isinstance(data, dict) else {}

    seconds = dto.get("sleepTimeSeconds")
    if seconds is None:
        stage_seconds = sum(
            int(dto.get(k) or 0)
            for k in ("deepSleepSeconds", "lightSleepSeconds", "remSleepSeconds")
        )
        if stage_seconds > 0:
            seconds = stage_seconds

    if seconds is None:
        return None

    score = None
    scores = None
    if isinstance(data, dict):
        scores = data.get("sleepScores")
    if not isinstance(scores, dict):
        scores = dto.get("sleepScores")
    if isinstance(scores, dict):
        overall = scores.get("overall") or scores.get("totalDuration")
        if isinstance(overall, dict):
            score = overall.get("value")
        elif isinstance(overall, (int, float)):
            score = overall
    if score is None:
        raw_score = dto.get("sleepScore")
        if isinstance(raw_score, (int, float)):
            score = raw_score

    start = _ts_to_iso(dto.get("sleepStartTimestampGMT") or dto.get("sleepStartTimestampLocal"))
    end = _ts_to_iso(dto.get("sleepEndTimestampGMT") or dto.get("sleepEndTimestampLocal"))

    return {
        "duration_minutes": int(seconds // 60),
        "score": int(score) if score is not None else None,
        "start_time": start,
        "end_time": end,
    }


def _normalize_sleep_need(data: Any) -> dict[str, Any] | None:
    if _is_error_payload(data):
        return None
    dto = data.get("dailySleepDTO") if isinstance(data, dict) else None
    if not dto or not isinstance(dto, dict):
        return None
    need = dto.get("sleepNeed")
    if not need or not isinstance(need, dict):
        return None

    baseline = need.get("baseline")
    actual = need.get("actual")
    slept_minutes = None
    if dto.get("sleepTimeSeconds") is not None:
        slept_minutes = int(dto["sleepTimeSeconds"] // 60)

    deficit = None
    if actual is not None and slept_minutes is not None:
        deficit = max(0, int(actual) - slept_minutes)

    return {
        "baseline_minutes": int(baseline) if baseline is not None else None,
        "actual_minutes": int(actual) if actual is not None else None,
        "feedback": need.get("feedback"),
        "deficit_minutes": deficit,
    }


def _normalize_respiration(data: Any) -> dict[str, Any] | None:
    if _is_error_payload(data):
        return None
    avg = data.get("avgSleepRespirationValue") or data.get("avgWakingRespirationValue")
    if avg is None and not _is_error_payload(data.get("stats") if isinstance(data, dict) else None):
        pass
    stats = data if isinstance(data, dict) else {}
    avg = avg or stats.get("avgSleepRespiration") or stats.get("lowestRespirationValue")
    if avg is None:
        return None
    return {"avg": float(avg)}


def _normalize_spo2(spo2_data: Any, sleep_data: Any) -> dict[str, Any] | None:
    avg = None
    minimum = None

    if not _is_error_payload(spo2_data):
        readings = spo2_data.get("spO2HourlyAverages") or []
        values = [
            r.get("spO2Value")
            for r in readings
            if isinstance(r, dict) and r.get("spO2Value") is not None
        ]
        if values:
            avg = round(sum(values) / len(values), 1)
            minimum = min(values)
        elif spo2_data.get("averageSpO2") is not None:
            avg = float(spo2_data["averageSpO2"])

    if avg is None and not _is_error_payload(sleep_data):
        dto = sleep_data.get("dailySleepDTO") or {}
        if isinstance(dto, dict) and dto.get("averageSpO2Value") is not None:
            avg = float(dto["averageSpO2Value"])
        if isinstance(dto, dict) and dto.get("lowestSpO2Value") is not None:
            minimum = float(dto["lowestSpO2Value"])

    if avg is None:
        return None
    result: dict[str, Any] = {"avg": avg}
    if minimum is not None:
        result["min"] = minimum
    return result


def _normalize_temp(data: Any) -> dict[str, Any] | None:
    if _is_error_payload(data):
        return None
    deviation = data.get("sleepTempDeviation") or data.get("deviation")
    if deviation is None:
        return None
    return {"deviation_c": float(deviation)}


def metrics_to_raw(metrics: dict[str, Any], brief_date: str) -> RawMetrics:
    """Build RawMetrics from normalized metrics dict."""
    raw = RawMetrics(date=date.fromisoformat(brief_date))

    hrv = metrics.get("hrv") or {}
    if hrv.get("value") is not None:
        raw.hrv_ms = float(hrv["value"])

    hr = metrics.get("heart_rate") or {}
    if hr.get("resting") is not None:
        raw.resting_hr_bpm = float(hr["resting"])

    resp = metrics.get("respiration") or {}
    if resp.get("avg") is not None:
        raw.respiratory_rate = float(resp["avg"])

    temp = metrics.get("temp") or {}
    if temp.get("deviation_c") is not None:
        raw.temp_deviation_c = float(temp["deviation_c"])

    spo2 = metrics.get("spo2") or {}
    if spo2.get("avg") is not None:
        raw.spo2_avg_pct = float(spo2["avg"])
    if spo2.get("min") is not None:
        raw.spo2_min_pct = float(spo2["min"])

    sleep = metrics.get("sleep") or {}
    if sleep.get("duration_minutes") is not None:
        raw.total_sleep_seconds = int(sleep["duration_minutes"]) * 60
    if sleep.get("deep_minutes") is not None:
        raw.deep_sleep_seconds = int(sleep["deep_minutes"]) * 60
    if sleep.get("rem_minutes") is not None:
        raw.rem_sleep_seconds = int(sleep["rem_minutes"]) * 60

    return raw


def metrics_to_sleep_need(metrics: dict[str, Any]) -> SleepNeed | None:
    need = metrics.get("sleep_need")
    if not need:
        return None
    return SleepNeed(
        baseline_minutes=need.get("baseline_minutes"),
        actual_minutes=need.get("actual_minutes"),
        feedback=need.get("feedback"),
        deficit_minutes=need.get("deficit_minutes"),
    )


def _normalize_body_battery(data: Any, stats_data: Any = None) -> dict[str, Any] | None:
    if isinstance(data, list):
        data = data[0] if data else None

    if not _is_error_payload(data):
        result = _body_battery_from_record(data)
        if result:
            return result

    if not _is_error_payload(stats_data):
        return _body_battery_from_stats(stats_data)

    return None


def _body_battery_level(value: Any) -> int | None:
    if value is None or isinstance(value, str):
        return None
    return int(value)


def _body_battery_from_record(data: dict[str, Any]) -> dict[str, Any] | None:
    values = data.get("bodyBatteryValuesArray") or data.get("bodyBatteryValues") or []
    if not values:
        return None

    levels: list[int] = []
    for entry in values:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        level = _body_battery_level(entry[1] if len(entry) == 2 else entry[2])
        if level is not None:
            levels.append(level)

    if not levels:
        return None

    current = levels[-1]
    minimum = min(levels)
    maximum = max(levels)
    overnight_levels = levels[: max(1, len(levels) // 3)]
    overnight_charge = current - overnight_levels[0]

    charged = data.get("charged")
    return {
        "current": current,
        "overnight_charge": int(charged) if charged is not None else overnight_charge,
        "min": minimum,
        "max": maximum,
    }


def _body_battery_from_stats(stats: dict[str, Any]) -> dict[str, Any] | None:
    current = stats.get("bodyBatteryMostRecentValue")
    if current is None:
        return None

    charged = stats.get("bodyBatteryChargedValue")
    return {
        "current": int(current),
        "overnight_charge": int(charged) if charged is not None else None,
        "min": int(stats["bodyBatteryLowestValue"]) if stats.get("bodyBatteryLowestValue") else None,
        "max": int(stats["bodyBatteryHighestValue"]) if stats.get("bodyBatteryHighestValue") else None,
    }


def _normalize_stress(data: Any) -> dict[str, Any] | None:
    if _is_error_payload(data):
        return None

    values_arr = data.get("stressValuesArray") or data.get("stressValues") or []
    levels = [
        v[1]
        for v in values_arr
        if isinstance(v, (list, tuple)) and len(v) >= 2 and v[1] is not None and v[1] >= 0
    ]
    if not levels:
        avg = data.get("avgStressLevel")
        if avg is None:
            return None
        return {"avg": int(avg), "max": int(avg), "overnight_avg": int(avg)}

    overnight = levels[: max(1, len(levels) // 3)]
    return {
        "avg": int(sum(levels) / len(levels)),
        "max": int(max(levels)),
        "overnight_avg": int(sum(overnight) / len(overnight)),
    }


def _normalize_heart_rate(hr_data: Any, stats_data: Any) -> dict[str, Any] | None:
    resting = None
    avg = None

    if not _is_error_payload(hr_data):
        resting = hr_data.get("restingHeartRate")
        hr_values = hr_data.get("heartRateValues") or []
        valid = [
            v[1]
            for v in hr_values
            if isinstance(v, (list, tuple)) and len(v) >= 2 and v[1] is not None and v[1] > 0
        ]
        if valid:
            avg = int(sum(valid) / len(valid))

    if resting is None and not _is_error_payload(stats_data):
        resting = stats_data.get("restingHeartRate")

    if resting is None and avg is None:
        return None

    return {
        "resting": int(resting) if resting is not None else None,
        "avg": avg,
    }


def _normalize_hrv(data: Any) -> dict[str, Any] | None:
    if _is_error_payload(data):
        return None

    summary = data.get("hrvSummary") or data.get("summary") or data
    if not isinstance(summary, dict):
        return None

    value = summary.get("lastNightAvg") or summary.get("weeklyAvg") or summary.get("lastNight")
    if value is None:
        return None

    status_raw = (
        summary.get("status")
        or summary.get("hrvStatus")
        or summary.get("baselineStatus")
        or "unknown"
    )
    status = _map_hrv_status(str(status_raw))

    return {"status": status, "value": int(value)}


def _normalize_training(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        preferred = None
        for item in data:
            if isinstance(item, dict) and item.get("inputContext") == "AFTER_WAKEUP_RESET":
                preferred = item
                break
        data = preferred or (data[0] if data else None)

    if _is_error_payload(data):
        return None

    if not isinstance(data, dict):
        return None

    readiness = (
        data.get("score")
        or data.get("overallScore")
        or data.get("readinessScore")
        or data.get("trainingReadinessScore")
    )
    recovery_hours = (
        data.get("recoveryTime")
        or data.get("recoveryTimeHours")
        or data.get("recoveryTimeInHours")
    )

    if readiness is None and recovery_hours is None:
        # Some accounts return nested structure
        most_recent = data.get("mostRecentTrainingStatus") or data.get("latest")
        if isinstance(most_recent, dict):
            readiness = most_recent.get("overallScore") or most_recent.get("score")
            recovery_hours = most_recent.get("recoveryTime")

    if readiness is None and recovery_hours is None:
        return None

    result: dict[str, Any] = {}
    if readiness is not None:
        result["readiness"] = int(readiness)
    if recovery_hours is not None:
        result["recovery_time_hours"] = int(recovery_hours)
    return result or None


def _ts_to_iso(ts: Any) -> str | None:
    if ts is None:
        return None
    try:
        ts_int = int(ts)
        if ts_int > 1_000_000_000_000:
            ts_int //= 1000
        return datetime.fromtimestamp(ts_int, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(ts)


def _map_hrv_status(raw: str) -> str:
    lower = raw.lower()
    if "balance" in lower or "balanced" in lower or "normal" in lower:
        return "balanced"
    if "low" in lower or "unbalance" in lower or "poor" in lower:
        return "low"
    if "high" in lower:
        return "high"
    return raw
