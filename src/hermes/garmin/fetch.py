"""Resilient Garmin data fetching."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    date: str
    fetched_at: str
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    sleep_source_date: str | None = None

    def has_sleep(self) -> bool:
        sleep = self.data.get("sleep")
        if not sleep or (isinstance(sleep, dict) and (sleep.get("_error") or sleep.get("_empty"))):
            return False
        return _sleep_has_data(sleep)

    def has_recovery_metric(self) -> bool:
        checks = [
            lambda: _body_battery_has_data(self.data.get("body_battery")),
            lambda: _body_battery_has_data(self.data.get("stress")),
            lambda: _stress_has_data(self.data.get("stress")),
            lambda: _heart_rate_has_data(self.data.get("heart_rate")),
            lambda: _stats_has_recovery(self.data.get("stats")),
            lambda: self.has_hrv(),
        ]
        return any(check() for check in checks)

    def has_hrv(self) -> bool:
        return _hrv_has_data(self.data.get("hrv"))


def _sleep_dto(sleep: Any) -> dict[str, Any]:
    if not sleep or not isinstance(sleep, dict):
        return {}
    dto = sleep.get("dailySleepDTO") or sleep.get("sleep") or sleep
    return dto if isinstance(dto, dict) else {}


def _sleep_has_data(sleep: Any) -> bool:
    dto = _sleep_dto(sleep)
    if not dto:
        return False

    if dto.get("sleepTimeSeconds") is not None:
        return True

    if any(dto.get(k) is not None for k in ("sleepStartTimestampGMT", "sleepEndTimestampGMT")):
        return True

    stage_seconds = sum(
        int(dto.get(k) or 0)
        for k in ("deepSleepSeconds", "lightSleepSeconds", "remSleepSeconds", "awakeSleepSeconds")
    )
    return stage_seconds > 0


def _sleep_wake_on_date(sleep: Any, target_date: str) -> bool:
    dto = _sleep_dto(sleep)
    for key in ("sleepEndTimestampLocal", "sleepEndTimestampGMT", "autoSleepEndTimestampGMT"):
        end = dto.get(key)
        if end is None:
            continue
        end_str = str(end)
        if end_str.startswith(target_date):
            return True
        if end_str[:10] == target_date:
            return True
    return False


def _unwrap_body_battery_record(data: Any) -> dict[str, Any] | None:
    if not data:
        return None
    if isinstance(data, list):
        return data[0] if data and isinstance(data[0], dict) else None
    if isinstance(data, dict) and not data.get("_error") and not data.get("_empty"):
        if "bodyBatteryValuesArray" in data or "bodyBatteryValues" in data:
            return data
    return None


def _body_battery_has_data(data: Any) -> bool:
    record = _unwrap_body_battery_record(data)
    if not record:
        return False
    values = record.get("bodyBatteryValuesArray") or record.get("bodyBatteryValues") or []
    return bool(values)


def _stress_has_data(data: Any) -> bool:
    if not data or not isinstance(data, dict) or data.get("_error") or data.get("_empty"):
        return False
    values = data.get("stressValuesArray") or data.get("stressValues") or []
    return bool(values)


def _heart_rate_has_data(data: Any) -> bool:
    if not data or not isinstance(data, dict) or data.get("_error") or data.get("_empty"):
        return False
    return data.get("restingHeartRate") is not None or bool(data.get("heartRateValues"))


def _stats_has_recovery(data: Any) -> bool:
    if not data or not isinstance(data, dict) or data.get("_error") or data.get("_empty"):
        return False
    return (
        data.get("restingHeartRate") is not None
        or data.get("bodyBatteryMostRecentValue") is not None
        or data.get("averageStressLevel") is not None
    )


def _hrv_has_data(data: Any) -> bool:
    if not data or not isinstance(data, dict) or data.get("_error") or data.get("_empty"):
        return False
    summary = data.get("hrvSummary") or data.get("summary") or data
    if isinstance(summary, dict):
        return summary.get("lastNightAvg") is not None or summary.get("weeklyAvg") is not None
    return False


def safe_api_call(
    api_method: Callable[..., Any], *args: Any, **kwargs: Any
) -> tuple[bool, Any | None, str | None]:
    try:
        result = api_method(*args, **kwargs)
        return True, result, None
    except GarminConnectAuthenticationError as exc:
        return False, None, f"Authentication error: {exc}"
    except GarminConnectTooManyRequestsError as exc:
        return False, None, f"Rate limit exceeded: {exc}"
    except GarminConnectConnectionError as exc:
        error_str = str(exc)
        if "400" in error_str:
            return False, None, "Not available (400)"
        if "401" in error_str:
            return False, None, "Authentication required (401)"
        if "403" in error_str:
            return False, None, "Access denied (403)"
        if "404" in error_str:
            return False, None, "Not found (404)"
        if "429" in error_str:
            return False, None, "Rate limit (429)"
        if "500" in error_str:
            return False, None, "Server error (500)"
        return False, None, f"Connection error: {exc}"
    except Exception as exc:
        return False, None, f"Unexpected error: {exc}"


def _store_source(
    result: FetchResult,
    key: str,
    ok: bool,
    data: Any | None,
    err: str | None,
) -> None:
    if ok:
        if data is None or data == [] or data == {}:
            result.data[key] = {"_empty": True}
            logger.debug("%s not available for %s (empty response)", key, result.date)
        else:
            result.data[key] = data
            logger.debug("Fetched %s for %s", key, result.date)
    else:
        result.data[key] = {"_error": err or "Unknown error"}
        result.errors.append({"source": key, "error": err or "Unknown error"})
        logger.warning("Failed to fetch %s: %s", key, err)


def _fetch_sleep_with_fallback(client: Garmin, date: str) -> tuple[Any, str | None]:
    ok, data, err = safe_api_call(client.get_sleep_data, date)
    if ok and data and _sleep_has_data(data):
        return data, date

    prev_date = (datetime.strptime(date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
    ok_prev, prev_data, _ = safe_api_call(client.get_sleep_data, prev_date)
    if ok_prev and prev_data and _sleep_has_data(prev_data) and _sleep_wake_on_date(prev_data, date):
        logger.info("Using sleep from %s (wake on %s)", prev_date, date)
        return prev_data, prev_date

    if ok and data is not None:
        return data, date
    return {"_empty": True}, None


def fetch_recovery_data(client: Garmin, date: str) -> FetchResult:
    """Fetch all recovery metrics for a date; failures are isolated per source."""
    result = FetchResult(
        date=date,
        fetched_at=datetime.utcnow().isoformat() + "Z",
    )

    sleep_data, sleep_source = _fetch_sleep_with_fallback(client, date)
    result.data["sleep"] = sleep_data
    result.sleep_source_date = sleep_source

    sources: list[tuple[str, Callable[..., Any]]] = [
        ("stats", client.get_stats),
        ("heart_rate", client.get_heart_rates),
        ("stress", client.get_stress_data),
        ("body_battery", client.get_body_battery),
        ("hrv", client.get_hrv_data),
        ("training_readiness", client.get_training_readiness),
    ]

    for key, method in sources:
        ok, data, err = safe_api_call(method, date)
        _store_source(result, key, ok, data, err)

    extra_sources: list[tuple[str, Callable[..., Any]]] = []
    if hasattr(client, "get_respiration_data"):
        extra_sources.append(("respiration", client.get_respiration_data))
    if hasattr(client, "get_spo2_data"):
        extra_sources.append(("spo2", client.get_spo2_data))
    if hasattr(client, "get_skin_temperature"):
        extra_sources.append(("skin_temp", client.get_skin_temperature))

    for key, method in extra_sources:
        ok, data, err = safe_api_call(method, date)
        _store_source(result, key, ok, data, err)

    return result
