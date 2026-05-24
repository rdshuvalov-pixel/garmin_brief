---
name: garmin-brief
description: "Утренний recovery-бриф из Garmin Connect: scoring Green/Yellow/Red/Grey, Telegram + LLM HTML, VPS-хостинг."
version: 1.0.0
author: "rdshuvalov-pixel"
license: MIT
required_env:
  - GARMIN_EMAIL
  - GARMIN_PASSWORD
  - OPENROUTER_API_KEY
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_CHAT_ID
  - BRIEF_PUBLIC_BASE_URL
tags: [Garmin, Health, Morning Brief, Telegram, Cron, VPS]
homepage: "https://github.com/rdshuvalov-pixel/garmin_brief"
---

# Garmin Brief (Hermes)

Утренний recovery-бриф из Garmin Connect: детерминированный scoring (Green/Yellow/Red/Grey), короткий Telegram + полный LLM-текст в HTML.

**Корень навыка:** любой путь после `git clone`.  
**VPS (рекомендуется):** `/opt/garmin-brief`

## Когда использовать

- вопросы про утренний бриф Garmin / recovery / HRV / статус дня
- ручной запуск, пересборка или отладка брифа
- не пришёл Telegram или ссылка на HTML не открывается
- деплой или обновление на VPS
- первая авторизация Garmin (MFA)

## Архитектура

```
cron (07:00–08:30, каждые 15 мин)
  → scripts/run_morning_brief.py --attempt N
  → fetch Garmin → normalize → SQLite baselines → signal_scorer (без LLM)
  → generate_telegram (шаблон) + build_narrative (OpenRouter LLM)
  → save data/briefs/morning_YYYY-MM-DD.json
  → publish_html → web/briefs/YYYY-MM-DD.html
  → Telegram (короткий текст + brief_url)
```

**LLM не выбирает статус дня** — только пишет развёрнутый markdown в `brief_html`.

Правила интерпретации метрик: `docs/metrics-guide.md`

## Переменные окружения

См. `.env.example`. Параметры по умолчанию — в `config.yaml`.

На VPS `BRIEF_PUBLIC_BASE_URL` должен быть публичным URL, не `127.0.0.1`.

## Команды (из корня навыка)

```bash
export HERMES_GARMIN_ROOT="$(git rev-parse --show-toplevel)"
PROJECT="${HERMES_GARMIN_ROOT:-/opt/garmin-brief}"
cd "$PROJECT"
PY=.venv/bin/python
```

| Действие | Команда |
|----------|---------|
| Garmin MFA (один раз) | `$PY scripts/login.py` |
| Запуск брифа | `$PY scripts/run_morning_brief.py --force --attempt 7` |
| Пересборка HTML | `$PY scripts/publish_brief.py --date YYYY-MM-DD` |
| Веб-сервер | `$PY scripts/serve_brief.py --host 0.0.0.0 --port 8765` |

Cron: `cron/morning-brief.cron.example` (локально), `deploy/morning-brief.cron.vps` (VPS).

## Артефакты

| Файл | Содержимое |
|------|------------|
| `data/raw/garmin_YYYY-MM-DD.json` | сырой fetch |
| `data/briefs/morning_YYYY-MM-DD.json` | полный бриф + `brief_html` |
| `web/briefs/YYYY-MM-DD.html` | опубликованная страница |

## Деплой на VPS

```bash
git clone https://github.com/rdshuvalov-pixel/garmin_brief.git /opt/garmin-brief
cd /opt/garmin-brief
cp .env.example .env && nano .env
bash deploy/install-vps.sh
.venv/bin/python scripts/login.py
```

## Чего не делать

- Не менять Green/Yellow/Red через LLM — только `signal_scorer`
- Не коммитить `.env` и Garmin-токены
- Не ставить `BRIEF_PUBLIC_BASE_URL=http://127.0.0.1` на VPS с Telegram
