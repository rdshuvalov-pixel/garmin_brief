# Hermes skills (Garmin morning brief)

Skill лежит **в репозитории**, не только в `~/.hermes/`.

```
skills/garmin-morning-brief/
├── SKILL.md                      ← инструкция для Hermes Agent
└── references/
    └── metrics-guide.md          ← правила интерпретации метрик
```

## Подключить Hermes

**Способ 1 — external_dirs** (рекомендуется, skill остаётся в проекте):

В `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - "/path/to/hermes-garmin/skills"
```

Локально путь можно получить так:

```bash
export HERMES_GARMIN_ROOT="$(git -C /path/to/hermes-garmin rev-parse --show-toplevel)"
# external_dirs: ["${HERMES_GARMIN_ROOT}/skills"]
```

**Способ 2 — симлинк в ~/.hermes/skills:**

```bash
ln -sf "/path/to/hermes-garmin/skills/garmin-morning-brief" \
  ~/.hermes/skills/health/garmin-morning-brief
```

**Способ 3 — явно в чате:**

```bash
hermes chat --skills garmin-morning-brief \
  --workdir "/path/to/hermes-garmin"
```

## Cron Hermes

```bash
hermes cron add "every day at 8:30" \
  "Garmin morning brief attempt 7" \
  --skill garmin-morning-brief \
  --workdir "/path/to/hermes-garmin"
```

Секреты — в `~/.hermes/.env` (скопировать из `.env` проекта, не коммитить).
