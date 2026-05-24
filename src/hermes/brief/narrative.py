"""Full morning narrative via OpenRouter (LLM) with template fallback."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from hermes.analysis.signal_scorer import DayStatus, ScoreResult
from hermes.brief.serialize import STATUS_EMOJI, STATUS_LABEL, build_llm_context
from hermes.config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — персональный health-аналитик, который каждое утро пишет полный брифинг по данным Garmin.

ТВОЙ СТИЛЬ:
— Прямой, конкретный, без воды и без паники
— Пишешь как умный тренер, который знает историю человека
— Тон спокойный, но честный

ПРАВИЛА (строго):
1. Не ставишь диагнозы
2. Не делаешь вывод по одной метрике — только связки
3. Сравниваешь только с личной нормой из контекста
4. Не усиливаешь тревожность

СТРУКТУРА (markdown):
1. Заголовок со статусом дня (Green/Yellow/Red/Grey)
2. Главная причина (1–3 предложения)
3. Ключевые метрики (краткий список)
4. План на день: физическая нагрузка, работа, восстановление
5. Watchlist на завтра (один абзац)

Язык: русский. Длина: средний формат, не сухой дашборд."""


def build_narrative(
    result: ScoreResult,
    metrics: dict[str, Any],
    config: Config,
) -> str:
    if not config.openrouter_api_key:
        logger.info("OPENROUTER_API_KEY not set — using fallback template")
        return _fallback_template(result)

    context = build_llm_context(result, metrics)
    user_message = f"""Вот данные утреннего отчёта:

{context}

Напиши полный утренний бриф по правилам из системного промпта."""

    try:
        text = _call_openrouter(config, user_message)
        logger.info("Narrative generated via OpenRouter (%d chars)", len(text))
        return text
    except Exception as exc:
        logger.error("OpenRouter failed: %s — using fallback", exc)
        return _fallback_template(result)


def _extract_message_content(message: dict[str, Any]) -> str:
    """OpenAI-compatible content; Qwen3 may return null content + reasoning_details."""
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str) and block.strip():
                parts.append(block.strip())
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n".join(parts)

    reasoning = message.get("reasoning")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning.strip()

    details = message.get("reasoning_details") or []
    if isinstance(details, list):
        parts = []
        for item in details:
            if not isinstance(item, dict):
                continue
            if item.get("type") in ("reasoning.text", "text"):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n\n".join(parts)

    return ""


def _call_openrouter(config: Config, user_message: str) -> str:
    payload = {
        "model": config.llm_model,
        "max_tokens": 900,
        # Qwen3.6 defaults to thinking mode — content is null without this
        "reasoning": {"enabled": False},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.openrouter_api_key}",
            "HTTP-Referer": config.brief_public_base_url,
            "X-Title": "Hermes Morning Brief",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}") from exc

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenRouter empty response: {body}")

    message = choices[0].get("message") or {}
    content = _extract_message_content(message)
    if not content:
        raise RuntimeError(
            f"OpenRouter returned empty content (message keys: {list(message.keys())})"
        )
    return content


def _fallback_template(result: ScoreResult) -> str:
    emoji = STATUS_EMOJI[result.day_status]
    label = STATUS_LABEL[result.day_status]
    reasons = "\n".join(f"- {r}" for r in result.top_reasons[:3]) or "- Данные получены."

    plan = {
        DayStatus.GREEN: (
            "**Физическая нагрузка:** можно интенсивную или умеренную тренировку.\n"
            "**Работа:** сложные задачи равномерно по дню.\n"
            "**Восстановление:** стандартный режим."
        ),
        DayStatus.YELLOW: (
            "**Физическая нагрузка:** зона 2, прогулка, mobility — без HIIT.\n"
            "**Работа:** важное — в первую половину дня.\n"
            "**Восстановление:** лечь раньше, кофе до обеда."
        ),
        DayStatus.RED: (
            "**Физическая нагрузка:** только лёгкая прогулка или отдых.\n"
            "**Работа:** минимум нагрузки, без переговоров на износ.\n"
            "**Восстановление:** сон и гидратация в приоритете."
        ),
        DayStatus.GREY: (
            "**Физическая нагрузка:** по самочувствию.\n"
            "**Работа:** без критичных решений на основании данных.\n"
            "**Восстановление:** проверить синхронизацию часов."
        ),
    }[result.day_status]

    watchlist = (
        "Завтра проверить: HRV ближе к базе, пульс покоя стабилен, "
        "сон подтверждён полностью."
    )

    return (
        f"## {emoji} {label}\n\n"
        f"### Главное\n{reasons}\n\n"
        f"### План на день\n{plan}\n\n"
        f"### Watchlist\n{watchlist}"
    )
