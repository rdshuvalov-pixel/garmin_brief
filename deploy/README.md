# Деплой garmin-brief

## Режимы хостинга HTML

| Режим | Когда | HTML |
|-------|-------|------|
| **vercel** (рекомендуется) | VPS + Vercel | HTTPS на Vercel |
| **local** | только VPS | systemd `:8765` |

Подробно: [docs/deploy-vercel.md](../docs/deploy-vercel.md)

## VPS + Vercel (рекомендуется)

**Первый раз** (создаёт `/opt/garmin-brief`, клонирует репо, ставит venv):

```bash
# на VPS от root, после git pull этого скрипта в репо:
bash deploy/bootstrap-vps.sh

# или вручную:
mkdir -p /opt
git clone https://github.com/rdshuvalov-pixel/garmin_brief.git /opt/garmin-brief
cd /opt/garmin-brief
cp .env.example .env && nano .env
apt install -y nodejs git
BRIEF_HOST=vercel bash deploy/install-vps.sh
.venv/bin/python scripts/login.py
crontab -e   # deploy/morning-brief.cron.vps
```

**Обновления с GitHub:**

```bash
cd /opt/garmin-brief && git pull && .venv/bin/pip install -e .
```

## VPS только (legacy)

```bash
BRIEF_HOST=local bash deploy/install-vps.sh
# systemd hermes-brief-web на порту 8765
```

## Файлы

| Файл | Назначение |
|------|------------|
| `bootstrap-vps.sh` | первый раз: mkdir + git clone + install |
| `install-vps.sh` | venv, cron hint; systemd только при `BRIEF_HOST=local` |
| `morning-brief.cron.vps` | 8 утренних poll'ов |
| `hermes-brief-web.service` | локальный web (режим local) |
| `../vercel.json` | конфиг Vercel (output: web) |
| `../scripts/deploy_vercel.sh` | ручной деплoy HTML |

## Hermes agent

```bash
hermes chat --skills garmin-brief --workdir "/opt/garmin-brief"
```
