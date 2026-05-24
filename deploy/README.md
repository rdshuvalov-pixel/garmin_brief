# Деплой HTML-брифов на VPS

Рекомендуемый путь на сервере: `/opt/hermes-garmin`

## Быстрый старт

```bash
# 1. С локальной машины — скопировать проект (без .venv и data)
#    Выполнять из корня клона репозитория:
rsync -avz --exclude .venv --exclude data --exclude .git --exclude .env \
  ./ \
  root@YOUR_VPS:/opt/hermes-garmin/

# Или на VPS — git clone:
# git clone https://github.com/USERNAME/hermes-garmin.git /opt/hermes-garmin

# 2. На VPS — установка
ssh root@YOUR_VPS
cp /path/to/.env /opt/hermes-garmin/.env   # или создать из .env.example
# В .env обязательно:
#   BRIEF_PUBLIC_BASE_URL=http://YOUR_VPS_IP:8765

bash /opt/hermes-garmin/deploy/install-vps.sh

# 3. Garmin MFA (один раз)
cd /opt/hermes-garmin && .venv/bin/python scripts/login.py

# 4. Cron
crontab -e   # вставить строки из deploy/morning-brief.cron.vps

# 5. Проверка
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

Skill для агента: `skills/garmin-morning-brief/SKILL.md`

Подключение в cron Hermes или вручную:
```
/cron add "every day at 7:30" "Run Garmin morning brief attempt 7 if missing" --skill garmin-morning-brief
```

Или просто попроси Hermes: «запусти утренний Garmin бриф» — он подхватит skill по описанию.
