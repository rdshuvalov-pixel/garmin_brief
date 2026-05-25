# Garmin Brief

Hermes-навык: утренний recovery-бриф из Garmin Connect — scoring Green/Yellow/Red/Grey, Telegram и LLM HTML.

Репозиторий: [github.com/rdshuvalov-pixel/garmin_brief](https://github.com/rdshuvalov-pixel/garmin_brief)

## Структура навыка

```text
garmin-brief/
├── README.md           # этот файл
├── config.yaml         # параметры навыка (не секреты)
├── .env.example        # шаблон секретов
├── skills/SKILL.md     # метаданные для Hermes Agent
├── scripts/            # точки входа
├── src/                # основная логика (models, jobs, garmin, …)
├── docs/               # справочники
├── deploy/             # VPS: systemd, cron
├── tests/              # pytest
└── web/                # шаблоны и опубликованные HTML
```

## Установка

```bash
git clone https://github.com/rdshuvalov-pixel/garmin_brief.git
cd garmin_brief

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Заполнить .env — см. таблицу ниже
```

## Использование

```bash
.venv/bin/python scripts/login.py                              # Garmin MFA, один раз
.venv/bin/python scripts/run_morning_brief.py --force --attempt 7
.venv/bin/python scripts/serve_brief.py                      # http://127.0.0.1:8765/briefs/
.venv/bin/python scripts/publish_brief.py --date 2026-05-24  # HTML из JSON
```

## Переменные окружения

Скопируйте `.env.example` → `.env`. **Не коммитьте `.env`.**

| Переменная | Назначение |
|------------|------------|
| `GARMIN_EMAIL` | Логин Garmin Connect |
| `GARMIN_PASSWORD` | Пароль Garmin Connect |
| `GARMINTOKENS` | Каталог токенов (`~/.garminconnect`) |
| `DATA_DIR` | Каталог данных (дефолт в `config.yaml`) |
| `USER_ID` | Идентификатор пользователя |
| `TIMEZONE` | Часовой пояс |
| `OPENROUTER_API_KEY` | Ключ OpenRouter |
| `LLM_MODEL` | Модель OpenRouter |
| `TELEGRAM_BOT_TOKEN` | Токен бота |
| `TELEGRAM_CHAT_ID` | Chat ID |
| `BRIEF_PUBLIC_BASE_URL` | Публичный URL HTML (`https://….vercel.app`) |
| `VERCEL_TOKEN` | Токен Vercel (VPS, auto-deploy) |
| `VERCEL_ORG_ID` | ID организации Vercel |
| `VERCEL_PROJECT_ID` | ID проекта Vercel |
| `TRIGGER_SECRET` | Секрет для POST `/trigger` (VPS, Hermes Cloud) |
| `TRIGGER_PORT` | Порт trigger-сервера (8787) |

Несекретные дефолты — в `config.yaml`; env их перекрывает.

## Архитектура (VPS + Vercel + Hermes Cloud)

- **VPS** — cron + HTTP trigger, Garmin, генерация
- **Vercel** — публичные HTML (`/briefs/`)
- **Hermes Cloud** — `POST /trigger` на VPS, просмотр брифов через Vercel URL

Подробно: [docs/architecture.md](docs/architecture.md)

## Hermes Agent (Cloud)

Skill: [`skills/SKILL.md`](skills/SKILL.md)

**Не** полагайся на `--workdir` для prod — агент в облаке дергает webhook:

```bash
curl -X POST "$TRIGGER_URL/trigger" \
  -H "Authorization: Bearer $TRIGGER_SECRET" \
  -d '{"force": true, "attempt": 7}'
```

Локальная отладка с клоном репо:

```yaml
skills:
  external_dirs:
    - "/path/to/garmin_brief"
```

## VPS + Vercel

**VPS** — cron, Garmin, генерация. **Vercel** — публичные HTML-брифы.

```bash
git clone https://github.com/rdshuvalov-pixel/garmin_brief.git /opt/garmin-brief
cd /opt/garmin-brief
cp .env.example .env && nano .env
apt install -y nodejs
BRIEF_HOST=vercel bash deploy/install-vps.sh
.venv/bin/python scripts/login.py
```

Инструкция: [docs/deploy-vercel.md](docs/deploy-vercel.md) · [deploy/README.md](deploy/README.md)

## Локально (без Vercel)

```bash
.venv/bin/python scripts/serve_brief.py
# BRIEF_PUBLIC_BASE_URL=http://127.0.0.1:8765
```

## Тесты

```bash
.venv/bin/pytest tests/ -q
```

## Секреты

- Секреты только в `.env` (локально и на VPS)
- В репозитории — `.env.example` и `config.yaml` без ключей
- Garmin-токены — в `GARMINTOKENS`

## Лицензия

MIT
