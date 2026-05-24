# Подготовка навыка garmin-brief к GitHub

## Структура (Правила навыка.md)

```text
garmin-brief/
├── README.md
├── config.yaml
├── .env.example
├── skills/SKILL.md
├── scripts/
├── src/
├── docs/
├── tests/
├── deploy/
└── web/
```

## Git

```bash
cd /path/to/garmin_brief
git remote add origin https://github.com/rdshuvalov-pixel/garmin_brief.git
git push -u origin main
```

## VPS

```bash
git clone https://github.com/rdshuvalov-pixel/garmin_brief.git /opt/garmin-brief
cd /opt/garmin-brief
cp .env.example .env && nano .env
bash deploy/install-vps.sh
```

## Чеклист перед push

- [ ] `.env` не в commit
- [ ] `web/briefs/*.html` не в commit
- [ ] `skills/SKILL.md` с `required_env` и `homepage`
- [ ] `config.yaml` без секретов
- [ ] `pytest tests/ -q` проходит
