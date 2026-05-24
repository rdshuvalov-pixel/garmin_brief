---
name: garmin-morning-brief
description: "Operate Hermes Garmin morning recovery brief — fetch Garmin Connect, score Green/Yellow/Red/Grey, Telegram + LLM HTML brief, VPS static hosting."
version: 1.0.0
license: MIT
prerequisites:
  env_vars:
    - GARMIN_EMAIL
    - GARMIN_PASSWORD
    - OPENROUTER_API_KEY
    - TELEGRAM_BOT_TOKEN
    - TELEGRAM_CHAT_ID
    - BRIEF_PUBLIC_BASE_URL
  commands: [python3]
metadata:
  hermes:
    tags: [Garmin, Health, Morning Brief, Telegram, Cron, VPS]
    related_skills: []
---

# Garmin Morning Brief (Hermes)

Утренний recovery-бриф из Garmin Connect: детерминированный scoring (Green/Yellow/Red/Grey), короткий Telegram + полный LLM-текст в HTML.

**Корень проекта:** любой путь после `git clone` (локально или VPS).  
**Рекомендуемый путь на VPS:** `/opt/hermes-garmin`

## Когда использовать skill

- пользователь спрашивает про утренний бриф Garmin / recovery / HRV / статус дня
- нужно вручную запустить, пересобрать или отладить бриф
- не пришёл Telegram или ссылка на HTML не открывается
- деплой или обновление на VPS
- первая авторизация Garmin (MFA)

Триггеры (не исчерпывающий список): «утренний бриф», «Garmin brief», «перезапусти бриф», «почему ссылка не работает», «опубликуй HTML».

## Архитектура (кратко)

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

Правила интерпретации метрик:
- `references/metrics-guide.md` (копия в skill)
- `Навык утренние метрики Garmin.md` в корне проекта

## Переменные окружения (.env)

```bash
GARMIN_EMAIL=
GARMIN_PASSWORD=
GARMINTOKENS=~/.garminconnect

DATA_DIR=./data
USER_ID=main_user
TIMEZONE=Europe/Lisbon

OPENROUTER_API_KEY=
LLM_MODEL=qwen/qwen3.6-35b-a3b

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ОБЯЗАТЕЛЬНО на VPS — публичный URL, не 127.0.0.1
BRIEF_PUBLIC_BASE_URL=http://YOUR_VPS_IP:8765
```

Если `BRIEF_PUBLIC_BASE_URL` указывает на `127.0.0.1`, Telegram-ссылка **не откроется с телефона**.

## Команды (всегда из корня проекта)

```bash
# Локально (из корня клона):
export HERMES_GARMIN_ROOT="$(git rev-parse --show-toplevel)"
# На VPS или если переменная не задана — дефолт /opt/hermes-garmin
PROJECT="${HERMES_GARMIN_ROOT:-/opt/hermes-garmin}"

cd "$PROJECT"
PY=.venv/bin/python
```

### Первый вход Garmin (MFA один раз)

```bash
$PY scripts/login.py
```

### Ручной запуск брифа

```bash
# Финальная попытка (как 08:30 cron), пересоздать даже если уже есть
$PY scripts/run_morning_brief.py --force --attempt 7

# Конкретная дата
$PY scripts/run_morning_brief.py --date 2026-05-23 --force --attempt 7
```

### Только пересобрать HTML из JSON (без Garmin, без LLM)

```bash
$PY scripts/publish_brief.py --date 2026-05-23
```

### Локальный / VPS веб-сервер брифов

```bash
$PY scripts/serve_brief.py --host 0.0.0.0 --port 8765
# index: http://HOST:8765/briefs/
# бриф:  http://HOST:8765/briefs/YYYY-MM-DD.html
```

На VPS предпочтительно **systemd** (`deploy/hermes-brief-web.service`), не ручной запуск.

## Cron (автоматика)

Mac-пример: `cron/morning-brief.cron.example`  
VPS-пример: `deploy/morning-brief.cron.vps`

8 запусков: attempt 1–7 в 07:00–08:30 Europe/Lisbon. Brief создаётся **один раз**, когда есть сон + HRV, либо на attempt 7 (Grey без HRV).

**Важно:** путь в cron должен быть **реальным на той машине**, где крутится job. На VPS не использовать Mac-путь с пробелами.

## Артеfacts — где смотреть результат

| Файл | Содержимое |
|------|------------|
| `data/raw/garmin_YYYY-MM-DD.json` | сырой fetch |
| `data/briefs/morning_YYYY-MM-DD.json` | полный бриф + `brief_html` + `brief_url` |
| `web/briefs/YYYY-MM-DD.html` | опубликованная страница |
| `data/cron.log` | лог cron на VPS |

Проверка LLM:

```bash
$PY -c "import json; r=json.load(open('data/briefs/morning_$(date +%F).json')); print(len(r.get('brief_html','')), r.get('brief_url'))"
```

## Деплой на VPS

```bash
# Из корня локального клона:
rsync -avz --exclude .venv --exclude data --exclude .env \
  ./ \
  root@YOUR_VPS:/opt/hermes-garmin/

ssh root@YOUR_VPS 'bash /opt/hermes-garmin/deploy/install-vps.sh'
```

После деплоя:
1. `/opt/hermes-garmin/.env` — обновить `BRIEF_PUBLIC_BASE_URL`
2. `cd /opt/hermes-garmin && .venv/bin/python scripts/login.py` (MFA)
3. `systemctl status hermes-brief-web`
4. С телефона: `http://VPS_IP:8765/briefs/`

## Дерево решений

**Telegram пришёл, ссылка не открывается** → `BRIEF_PUBLIC_BASE_URL`, systemd, firewall 8765

**Telegram не пришёл** → `data/cron.log`, ручной `--force --attempt 7`, токены

**HTML пустой** → проверить `brief_html` в JSON, затем `publish_brief.py`

## Чего не делать

- Не менять Green/Yellow/Red через LLM — только `signal_scorer`
- Не коммитить `.env` и Garmin-токены
- Не ставить `BRIEF_PUBLIC_BASE_URL=http://127.0.0.1` на VPS с Telegram

## Verification checklist

- [ ] `morning_YYYY-MM-DD.json` существует, `brief_html` > 1500 символов
- [ ] `web/briefs/YYYY-MM-DD.html` существует
- [ ] `brief_url` совпадает с публичным URL
- [ ] `hermes-brief-web` active (VPS)
- [ ] Telegram: статус + рабочая ссылка
