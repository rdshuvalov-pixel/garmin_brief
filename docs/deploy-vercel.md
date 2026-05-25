# Деплой: VPS (генерация) + Vercel (HTML)

## Схема

См. полная диаграмма: [docs/architecture.md](architecture.md)

```text
VPS cron + HTTP trigger (:8787)     Vercel (CDN)
  run_morning_brief.py       →      web/briefs/*.html
  Hermes Cloud POST /trigger →      архив + навигация
  vercel deploy              →
```

- **VPS** — Garmin, cron, trigger, `.env`, `data/`
- **Vercel** — только статика
- **Hermes Cloud** — `POST /trigger`, чтение `/briefs/` на Vercel

## 1. Vercel (один раз)

### Вариант A — через GitHub (рекомендуется для первого деплоя)

1. [vercel.com](https://vercel.com) → Import → репозиторий `rdshuvalov-pixel/garmin_brief`
2. Framework: **Other**, Root Directory: `.`, Output: **`web`** (или подхватит `vercel.json`)
3. Deploy — получите URL вида `https://garmin-brief-xxx.vercel.app`
4. Account → Tokens → создать **VERCEL_TOKEN**

### Вариант B — только CLI

```bash
npm i -g vercel   # или npx
cd garmin_brief/web
vercel link       # привязать проект
cat ../.vercel/project.json   # orgId, projectId
```

## 2. Переменные на VPS

В `.env` на VPS:

```env
BRIEF_PUBLIC_BASE_URL=https://your-project.vercel.app

VERCEL_TOKEN=...
VERCEL_ORG_ID=...
VERCEL_PROJECT_ID=...

TRIGGER_SECRET=...       # openssl rand -hex 32
TRIGGER_PORT=8787
```

`BRIEF_PUBLIC_BASE_URL` **без** trailing slash.

Hermes Cloud: `TRIGGER_URL=http://VPS_IP:8787` (не коммитить secret в skill repo).

## 2b. HTTP trigger (Hermes Cloud)

После `TRIGGER_SECRET` в `.env` — `install-vps.sh` ставит `hermes-brief-trigger`.

```bash
ufw allow 8787/tcp
curl http://127.0.0.1:8787/health
curl -X POST http://127.0.0.1:8787/trigger \
  -H "Authorization: Bearer $TRIGGER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"force": true, "attempt": 7}'
```

## 3. VPS (первый раз)

На сервере (SSH):

```bash
# Вариант A — один скрипт (создаёт /opt/garmin-brief и клонирует репо)
curl -fsSL https://raw.githubusercontent.com/rdshuvalov-pixel/garmin_brief/main/deploy/bootstrap-vps.sh | bash

# Вариант B — вручную
sudo mkdir -p /opt/garmin-brief
sudo git clone https://github.com/rdshuvalov-pixel/garmin_brief.git /opt/garmin-brief
cd /opt/garmin-brief
cp .env.example .env && nano .env

# Node.js для npx vercel
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

BRIEF_HOST=vercel bash deploy/install-vps.sh
.venv/bin/python scripts/login.py
crontab -e   # deploy/morning-brief.cron.vps
```

`git clone` сам создаёт `/opt/garmin-brief`, если родитель `/opt` уже есть.  
`mkdir -p` нужен только если клонируешь в нестандартный путь.

### Обновления с GitHub

```bash
cd /opt/garmin-brief
git pull
.venv/bin/pip install -e .
```

`BRIEF_HOST=vercel` — **не** ставит systemd web-сервер (HTML на Vercel).

## 4. Ручной деплoy HTML

```bash
bash scripts/deploy_vercel.sh
```

После каждого утреннего брифа деплoy на Vercel запускается **автоматически**, если задан `VERCEL_TOKEN`.

## 5. Проверка

```bash
# VPS — генерация
.venv/bin/python scripts/run_morning_brief.py --force --attempt 7

# Vercel — в браузере
open "https://your-project.vercel.app/briefs/"
open "https://your-project.vercel.app/briefs/$(date +%F).html"
```

## Локальная разработка

Без Vercel:

```bash
.venv/bin/python scripts/serve_brief.py
# BRIEF_PUBLIC_BASE_URL=http://127.0.0.1:8765
```

Не задавайте `VERCEL_TOKEN` локально, если не хотите деплоить в prod.

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| `npx не найден` | `apt install nodejs` на VPS |
| Ссылка в Telegram 404 | Проверить `BRIEF_PUBLIC_BASE_URL` и успешность `deploy_vercel.sh` |
| `VERCEL_ORG_ID missing` | `vercel link` в `web/` или импорт проекта в Vercel UI |
