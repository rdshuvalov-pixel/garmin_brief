"""Publish self-contained HTML brief pages."""

from __future__ import annotations

import html
import logging
import re
from pathlib import Path
from typing import Any

from hermes.config import Config
from hermes.brief.vercel_deploy import deploy_vercel_if_configured

logger = logging.getLogger(__name__)

_STATUS_CLASS = {
    "green": "status-green",
    "yellow": "status-yellow",
    "red": "status-red",
    "grey": "status-grey",
}

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def build_sleep_section(metrics: dict[str, Any], day_status: str) -> dict[str, Any]:
    sleep = metrics.get("sleep") or {}
    bb = metrics.get("body_battery") or {}
    hrv = metrics.get("hrv") or {}

    hours = "—"
    if sleep.get("duration_minutes") is not None:
        h, m = divmod(int(sleep["duration_minutes"]), 60)
        hours = f"{h}ч {m}м"

    battery = f"{bb['current']}%" if bb.get("current") is not None else "—"
    hrv_val = str(hrv.get("value")) if hrv.get("value") is not None else "—"

    return {
        "hours": hours,
        "battery": battery,
        "hrv": hrv_val,
        "text": _status_text(day_status),
        "status_class": _STATUS_CLASS.get(day_status, "status-grey"),
    }


def _status_text(day_status: str) -> str:
    mapping = {
        "green": "Восстановление хорошее. Можно планировать активный день.",
        "yellow": "Восстановление частичное. Умеренный режим без пиковых нагрузок.",
        "red": "Восстановление снижено. Приоритет — отдых и сон.",
        "grey": "Данные неполные. Ориентируйся на самочувствие.",
    }
    return mapping.get(day_status, mapping["grey"])


def _inline_markdown(text: str) -> str:
    escaped = html.escape(text)

    def bold_replace(match: re.Match[str]) -> str:
        return f"<strong>{match.group(1)}</strong>"

    return _BOLD_RE.sub(bold_replace, escaped)


def markdown_to_html(text: str) -> str:
    """Markdown subset for LLM brief_html (#/##/###, -, * bullets, **bold**)."""
    lines = text.splitlines()
    out: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            close_list()
            continue

        if stripped.startswith("# "):
            close_list()
            out.append(f"<h1>{_inline_markdown(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            close_list()
            out.append(f"<h2>{_inline_markdown(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            close_list()
            out.append(f"<h3>{_inline_markdown(stripped[4:])}</h3>")
        elif stripped.startswith("- ") or re.match(r"^\*\s+", stripped):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = stripped[2:].strip() if stripped.startswith("- ") else re.sub(r"^\*\s+", "", stripped)
            out.append(f"<li>{_inline_markdown(item)}</li>")
        else:
            close_list()
            out.append(f"<p>{_inline_markdown(stripped)}</p>")

    close_list()
    return "\n".join(out)


def publish_html(config: Config, record: dict[str, Any]) -> Path:
    template_path = config.project_root / "web" / "templates" / "brief.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    date = record["date"]
    day_status = record.get("day_status", "grey")
    sections = record.get("sections") or {}
    sleep = sections.get("sleep") or build_sleep_section(
        record.get("garmin", {}).get("metrics", {}), day_status
    )

    brief_html = record.get("brief_html") or ""
    if not brief_html.strip():
        logger.warning("brief_html empty for %s — narrative section will be blank", date)

    narrative_html = markdown_to_html(brief_html)

    placeholders = {
        "{{DATE}}": html.escape(date),
        "{{DAY_STATUS}}": html.escape(day_status.upper()),
        "{{STATUS_CLASS}}": sleep.get("status_class", "status-grey"),
        "{{SLEEP_HOURS}}": html.escape(str(sleep.get("hours", "—"))),
        "{{SLEEP_BATTERY}}": html.escape(str(sleep.get("battery", "—"))),
        "{{SLEEP_HRV}}": html.escape(str(sleep.get("hrv", "—"))),
        "{{SLEEP_TEXT}}": html.escape(str(sleep.get("text", ""))),
        "{{NARRATIVE_HTML}}": narrative_html,
        "{{WEATHER_SECTION}}": _optional_section("Погода", sections.get("weather")),
        "{{FOOD_SECTION}}": _optional_section("Еда вчера", sections.get("food")),
        "{{MEETINGS_SECTION}}": _optional_section("Встречи вчера", sections.get("meetings")),
        "{{CHATS_SECTION}}": _optional_section("Чаты", sections.get("chats")),
        "{{TASKS_SECTION}}": _optional_section("Задачи на сегодня", sections.get("tasks")),
        "{{TOKENS_SECTION}}": _optional_section("Токены вчера", sections.get("tokens")),
    }

    page = template
    for key, value in placeholders.items():
        page = page.replace(key, value)

    config.web_briefs_dir.mkdir(parents=True, exist_ok=True)
    out_path = config.web_briefs_dir / f"{date}.html"
    out_path.write_text(page, encoding="utf-8")
    _write_briefs_index(config)
    logger.info("Published HTML to %s (%d bytes)", out_path, out_path.stat().st_size)
    deploy_vercel_if_configured(config.project_root)
    return out_path


def _write_briefs_index(config: Config) -> None:
    """Simple index listing available brief HTML files."""
    briefs_dir = config.web_briefs_dir
    dates = sorted(
        (p.stem for p in briefs_dir.glob("*.html") if p.name != "index.html"),
        reverse=True,
    )
    items = "\n".join(
        f'<li><a href="{html.escape(d)}.html">{html.escape(d)}</a></li>' for d in dates
    )
    index_html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"><title>Брифы</title></head>
<body><h1>Утренние брифы</h1><ul>{items or '<li>пока нет</li>'}</ul></body></html>"""
    (briefs_dir / "index.html").write_text(index_html, encoding="utf-8")


def _optional_section(label: str, data: Any) -> str:
    if data is None:
        return f"""<div class="section">
      <div class="section-label">{html.escape(label)}</div>
      <p class="section-text muted">нет данных</p>
    </div>"""
    if isinstance(data, str):
        text = data
    elif isinstance(data, dict) and data.get("text"):
        text = str(data["text"])
    else:
        text = str(data)
    return f"""<div class="section">
      <div class="section-label">{html.escape(label)}</div>
      <p class="section-text">{html.escape(text)}</p>
    </div>"""


def warn_if_local_brief_url(config: Config) -> None:
    url = config.brief_public_base_url
    if "127.0.0.1" in url or "localhost" in url:
        if config.telegram_bot_token and config.telegram_chat_id:
            logger.warning(
                "BRIEF_PUBLIC_BASE_URL=%s — ссылка в Telegram не откроется с телефона. "
                "Укажи URL Vercel (https://….vercel.app) или публичный IP VPS.",
                url,
            )
