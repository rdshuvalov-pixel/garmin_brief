# Hermes Garmin

Утренний recovery-бриф из Garmin Connect: детерминированный scoring (Green/Yellow/Red/Grey), короткое сообщение в Telegram и полный LLM-текст в HTML.

## Возможности

- Получение метрик восстановления из Garmin Connect (сон, HRV, Body Battery, stress)
- Scoring дня без LLM (`signal_scorer`)
- Короткий Telegram + развёрнутый текст через OpenRouter
- Публикация HTML в `web/briefs/`
- Cron с 8 попытками (07:00–08:30) и деплой на VPS

## Быстрый старт (локально)

```bash
git clone https://github.com/USERNAME/hermes-garmin.git
cd hermes-garmin

python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# Заполнить .env — см. таблицу ниже

.venv/bin/python scripts/login.py          # Garmin MFA, один раз
.venv/bin/python scripts/run_morning_brief.py --force --attempt 7
.venv/bin/python scripts/serve_brief.py    # http://127.0.0.1:8765/briefs/
```

## Переменные окружения

Скопируйте `.env.example` в `.env`. **Не коммитьте `.env`.**

| Переменная | Назначение |
|------------|------------|
| `GARMIN_EMAIL` | Логин Garmin Connect |
| `GARMIN_PASSWORD` | Пароль Garmin Connect |
| `GARMINTOKENS` | Каталог токенов (по умолчанию `~/.garminconnect`) |
| `DATA_DIR` | Каталог данных (по умолчанию `./data`) |
| `USER_ID` | Идентификатор пользователя |
| `TIMEZONE` | Часовой пояс (например `Europe/Lisbon`) |
| `OPENROUTER_API_KEY` | Ключ OpenRouter для LLM-текста |
| `LLM_MODEL` | Модель OpenRouter |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота |
| `TELEGRAM_CHAT_ID` | Chat ID для доставки |
| `BRIEF_PUBLIC_BASE_URL` | Публичный URL HTML-брифов (на VPS — IP/домен, не `127.0.0.1`) |

Опционально для cron/shell (Python не читает): `HERMES_GARMIN_ROOT=/opt/hermes-garmin`

## Структура проекта

```text
hermes-garmin/
├── src/hermes/           # основной код
├── scripts/              # login, run_morning_brief, serve_brief, publish_brief
├── skills/               # Hermes Agent skill
├── deploy/               # VPS: systemd, cron, nginx
├── cron/                 # пример cron для Mac/локально
├── web/templates/        # шаблон HTML
└── web/briefs/           # опубликованные брифы (генерируются, не в git)
```

## VPS

Рекомендуемый путь: `/opt/hermes-garmin`

```bash
git clone https://github.com/USERNAME/hermes-garmin.git /opt/hermes-garmin
cd /opt/hermes-garmin
cp .env.example .env && nano .env
bash deploy/install-vps.sh
.venv/bin/python scripts/login.py
# crontab ← deploy/morning-brief.cron.vps
```

Подробнее: [deploy/README.md](deploy/README.md)

## Hermes Agent

Skill: `skills/garmin-morning-brief/SKILL.md`

Подключение через `external_dirs` в `~/.hermes/config.yaml` — см. [skills/README.md](skills/README.md)

## Секреты

- Секреты только в `.env` (локально и на VPS)
- В репозитории — только `.env.example` без реальных значений
- Garmin-токены хранятся в `GARMINTOKENS` (по умолчанию `~/.garminconnect`)

## Лицензия

MIT (skill metadata)
