# Деплой HTML-брифов на VPS

Рекомендуемый путь: `/opt/garmin-brief`

## Быстрый старт

```bash
# На VPS — git clone (предпочтительно):
git clone https://github.com/rdshuvalov-pixel/garmin_brief.git /opt/garmin-brief
cd /opt/garmin-brief
cp .env.example .env && nano .env
bash deploy/install-vps.sh

# Или rsync из локального клона:
rsync -avz --exclude .venv --exclude data --exclude .git --exclude .env \
  ./ \
  root@YOUR_VPS:/opt/garmin-brief/

ssh root@YOUR_VPS 'bash /opt/garmin-brief/deploy/install-vps.sh'

# Garmin MFA (один раз)
cd /opt/garmin-brief && .venv/bin/python scripts/login.py

# Cron
crontab -e   # строки из deploy/morning-brief.cron.vps

# Проверка
curl -I http://127.0.0.1:8765/briefs/
.venv/bin/python scripts/publish_brief.py --date $(date +%F)
```

## Файлы

| Файл | Назначение |
|------|------------|
| `install-vps.sh` | venv, systemd, директории |
| `hermes-brief-web.service` | systemd unit для `serve_brief.py` |
| `morning-brief.cron.vps` | 8 утренних poll'ов |
| `nginx-brief.conf.example` | опционально HTTPS |

## Hermes agent

Skill: `skills/SKILL.md` (name: `garmin-brief`)

```bash
hermes chat --skills garmin-brief --workdir "/opt/garmin-brief"
```
