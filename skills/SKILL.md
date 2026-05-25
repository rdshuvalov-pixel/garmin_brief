---
name: garmin-brief
description: "Утренний recovery-бриф из Garmin Connect: scoring, Telegram + LLM HTML. VPS генерирует, Vercel отдаёт HTML."
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
tags: [Garmin, Health, Morning Brief, Telegram, Cron, VPS, Vercel]
homepage: "https://github.com/rdshuvalov-pixel/garmin_brief"
---

# Garmin Brief (Hermes)

Утренний recovery-бриф из Garmin Connect: детерминированный scoring (Green/Yellow/Red/Grey), короткий Telegram + полный LLM-текст в HTML.

**Prod VPS:** `/opt/garmin-brief`  
**HTML:** Vercel (`BRIEF_PUBLIC_BASE_URL`)  
**Архитектура:** `docs/architecture.md`

## Когда использовать

- утренний бриф Garmin / recovery / HRV
- ручной запуск или пересборка
- Telegram / ссылка не работает
- деплой VPS или Vercel
- Garmin MFA

## Архитектура (3 площадки)

```
VPS cron (07:00–08:30) ──→ run_morning_brief.py
Hermes Cloud POST /trigger ──→ run_morning_brief.py (тот же VPS)
  → Garmin → scoring → LLM → JSON + HTML
  → vercel deploy → https://….vercel.app/briefs/
  → Telegram
```

**Hermes Cloud не запускает Python локально** — только HTTP webhook на VPS или чтение URL Vercel.

## Hermes Cloud — удалённый запуск (основной)

Пользователь хранит на VPS: `TRIGGER_URL`, `TRIGGER_SECRET` (не в git).

```bash
# Health
curl -s "$TRIGGER_URL/health"

# Запустить бриф сейчас
curl -s -X POST "$TRIGGER_URL/trigger" \
  -H "Authorization: Bearer $TRIGGER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"force": true, "attempt": 7}'

# Статус последнего job
curl -s "$TRIGGER_URL/status" -H "Authorization: Bearer $TRIGGER_SECRET"
```

Пример: `TRIGGER_URL=http://VPS_IP:8787`

После 202 Accepted — бриф идёт 1–3 мин (Garmin + LLM). Ссылка: `$BRIEF_PUBLIC_BASE_URL/briefs/YYYY-MM-DD.html`

**Просмотр архива без VPS:**

```bash
curl -s "$BRIEF_PUBLIC_BASE_URL/briefs/"
# или конкретный день: .../briefs/2026-05-24.html
```

## VPS — команды по SSH

```bash
PROJECT=/opt/garmin-brief
PY=$PROJECT/.venv/bin/python
cd "$PROJECT"
```

| Действие | Команда |
|----------|---------|
| Garmin MFA | `$PY scripts/login.py` |
| Запуск брифа | `$PY scripts/run_morning_brief.py --force --attempt 7` |
| Пересборка HTML | `$PY scripts/publish_brief.py --date YYYY-MM-DD` |
| Все HTML + nav | `$PY scripts/republish_all_briefs.py` |
| Vercel deploy | `bash scripts/deploy_vercel.sh` |
| Trigger server | `$PY scripts/trigger_server.py` (systemd: `hermes-brief-trigger`) |

Cron: `deploy/morning-brief.cron.vps`

## Переменные (.env на VPS)

См. `.env.example`: Garmin, OpenRouter, Telegram, `BRIEF_PUBLIC_BASE_URL`, Vercel, `TRIGGER_SECRET`, `TRIGGER_PORT`.

## Чего не делать

- Не запускать бриф на Vercel (только статика)
- Не дублировать cron в Hermes Cloud
- Не менять Green/Yellow/Red через LLM
- Не коммитить `.env`
