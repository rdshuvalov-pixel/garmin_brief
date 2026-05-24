"""Morning recovery brief job orchestration."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from hermes.analysis.signal_scorer import DayStatus, score
from hermes.analysis.trend import build_snapshot
from hermes.brief.generator import generate_telegram_brief
from hermes.brief.narrative import build_narrative
from hermes.brief.publish import build_sleep_section, publish_html, warn_if_local_brief_url
from hermes.brief.serialize import score_to_dict
from hermes.config import FINAL_ATTEMPT, MORNING_BRIEF_TYPE, Config
from hermes.delivery.channels import DeliveryChannel, StdoutChannel
from hermes.garmin.auth import init_garmin_client
from hermes.garmin.fetch import FetchResult, fetch_recovery_data
from hermes.normalize.recovery import metrics_to_raw, metrics_to_sleep_need, normalize_recovery
from hermes.storage.history import load_history, save_metrics
from hermes.storage.json_store import exists_brief, save_morning_brief, save_raw

logger = logging.getLogger(__name__)


def is_brief_ready(fetch_result: FetchResult, attempt: int) -> tuple[bool, bool]:
    """
    Returns (ready, force_grey).
    force_grey=True when creating on final attempt without HRV.
    """
    if not fetch_result.has_sleep():
        return False, False
    if fetch_result.has_hrv():
        return True, False
    if attempt >= FINAL_ATTEMPT:
        return True, True
    return False, False


def run_morning_brief(
    config: Config,
    *,
    target_date: str | None = None,
    attempt: int = 1,
    force: bool = False,
    delivery: DeliveryChannel | None = None,
) -> int:
    """Run morning brief job. Returns 0 on success or graceful skip, 1 on error."""
    delivery = delivery or StdoutChannel()
    brief_date = target_date or datetime.now(config.timezone).date().isoformat()

    if not force and exists_brief(config, config.user_id, brief_date, MORNING_BRIEF_TYPE):
        logger.info("Brief already exists for %s — skipping", brief_date)
        return 0

    client = init_garmin_client(config, interactive=False)
    if client is None:
        logger.error("Garmin authentication failed")
        return 1

    fetch_result = fetch_recovery_data(client, brief_date)
    save_raw(config, brief_date, _fetch_to_dict(fetch_result))

    ready, force_grey = is_brief_ready(fetch_result, attempt)
    if not ready:
        if not fetch_result.has_sleep():
            logger.info("Sleep not available yet for %s (attempt %d)", brief_date, attempt)
        else:
            logger.info("HRV not available yet for %s (attempt %d) — waiting", brief_date, attempt)
        return 0

    metrics = normalize_recovery(fetch_result.data, brief_date)
    raw_metrics = metrics_to_raw(metrics, brief_date)
    sleep_need = metrics_to_sleep_need(metrics)

    save_metrics(raw_metrics, config.history_db_path)
    history = load_history(config.history_db_path, days=30, end_date=date.fromisoformat(brief_date))
    snapshot = build_snapshot(
        raw_metrics,
        history,
        sleep_need=sleep_need,
        force_grey=force_grey,
    )
    score_result = score(snapshot)
    if force_grey and score_result.day_status != DayStatus.GREY:
        score_result.day_status = DayStatus.GREY
        if not any("неполн" in r.lower() for r in score_result.top_reasons):
            score_result.top_reasons = (
                ["HRV не синхронизировался — данные могут быть неполными"]
                + score_result.top_reasons
            )[:3]

    brief_url = config.brief_url_for(brief_date)
    brief_telegram = generate_telegram_brief(score_result, brief_url=brief_url)
    brief_html = build_narrative(score_result, metrics, config)

    day_status = score_result.day_status.value
    sleep_section = build_sleep_section(metrics, day_status)

    record: dict[str, Any] = {
        "date": brief_date,
        "type": MORNING_BRIEF_TYPE,
        "user_id": config.user_id,
        "source": "garmin_connect",
        "day_status": day_status,
        "brief_url": brief_url,
        "brief_telegram": brief_telegram,
        "brief_html": brief_html,
        "garmin": {
            "metrics": metrics,
            "sleep_need": metrics.get("sleep_need"),
            "score": score_to_dict(score_result),
        },
        "sections": {
            "sleep": sleep_section,
            "weather": None,
            "food": None,
            "meetings": None,
            "chats": None,
            "tasks": None,
            "tokens": None,
        },
        "created_at": datetime.now(config.timezone).isoformat(),
        "status": "created",
        "attempt": attempt,
        "force_grey": force_grey,
    }

    save_morning_brief(config, record)
    warn_if_local_brief_url(config)
    html_path = publish_html(config, record)
    delivery.send(brief_telegram)
    logger.info(
        "Morning brief created for %s (status=%s, html=%s, url=%s)",
        brief_date,
        day_status,
        html_path,
        brief_url,
    )
    return 0


def _fetch_to_dict(result: FetchResult) -> dict:
    payload = {
        "date": result.date,
        "fetched_at": result.fetched_at,
        "data": result.data,
        "errors": result.errors,
    }
    if result.sleep_source_date:
        payload["sleep_source_date"] = result.sleep_source_date
    return payload
