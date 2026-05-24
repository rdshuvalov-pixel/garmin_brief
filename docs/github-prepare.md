# Подготовка проекта Hermes Garmin к выгрузке на GitHub

Цель: привести проект к аккуратной структуре, убрать секреты, подготовить `.gitignore`, README и первый commit для публикации в GitHub.

## 1. Структура проекта

```text
hermes-garmin/
├── README.md
├── .gitignore
├── .env.example
├── pyproject.toml
├── src/hermes/
├── scripts/
├── skills/garmin-morning-brief/
├── deploy/
├── cron/
├── web/templates/
├── web/briefs/.gitkeep
└── docs/
    └── github-prepare.md
```

## 2. Корневые файлы

### README.md

Основное описание, установка, переменные окружения, VPS и Hermes skill.

### `.env.example`

Только названия переменных, без секретов. Настоящий `.env` не выгружается.

### `pyproject.toml`

Зависимости и метаданные пакета `hermes-garmin`. Установка: `pip install -e .`

## 3. `.gitignore`

Исключить:

- `.env`, `.env.*` (кроме `.env.example`)
- `.venv/`, `__pycache__/`
- `data/` — сырые данные и JSON-брифы
- `web/briefs/*` — сгенерированные HTML (личные метрики)
- `garmin-morning_1/` — legacy
- логи, IDE, OS-файлы

## 4. Секреты

Проверка перед commit:

```bash
git check-ignore -v .env
find . -name ".env" -type f
rg -l "sk-or-|AAF|@gmail" --glob '!.env' .
```

`.env` остаётся локально, но не попадает в git.

## 5. Универсальные пути

Код Python использует относительные пути (`Path(__file__)`). В cron/shell/rsync — шаблон:

```bash
export HERMES_GARMIN_ROOT="$(git rev-parse --show-toplevel)"
PROJECT="${HERMES_GARMIN_ROOT:-/opt/hermes-garmin}"
PY="$PROJECT/.venv/bin/python"
```

VPS по умолчанию: `/opt/hermes-garmin`

## 6. Локальная проверка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# заполнить .env
.venv/bin/python scripts/login.py
.venv/bin/python scripts/run_morning_brief.py --force --attempt 7
```

## 7. Git

```bash
cd /path/to/hermes-garmin
git init
git branch -M main
git add .
git status   # .env не должен быть в списке
git commit -m "Initial public release of Hermes Garmin morning brief"
```

Репозиторий создавать **отдельно** от родительской папки `Cursor/` — только в каталоге проекта.

## 8. GitHub

Создать пустой репозиторий `hermes-garmin` (без README/.gitignore/license):

```bash
git remote add origin https://github.com/USERNAME/hermes-garmin.git
git push -u origin main
```

## 9. Проверка после push

На GitHub должны быть: README, `.gitignore`, `.env.example`, `src/`, `skills/`, `deploy/`.

Не должно быть: `.env`, `.venv/`, `data/`, HTML-брифов, паролей, токенов.

## 10. VPS после clone

```bash
git clone https://github.com/USERNAME/hermes-garmin.git /opt/hermes-garmin
cd /opt/hermes-garmin
cp .env.example .env && nano .env
bash deploy/install-vps.sh
.venv/bin/python scripts/login.py
# crontab ← deploy/morning-brief.cron.vps
```

## 11. Обновления

Локально:

```bash
git add .
git commit -m "Update Garmin skill"
git push
```

На VPS:

```bash
cd /opt/hermes-garmin
git pull
.venv/bin/pip install -e .
systemctl restart hermes-brief-web
```

`.env` на сервере не перезаписывается `git pull`.

## 12. Чеклист перед push

- [ ] `.env` не попадает в commit
- [ ] `.venv/` не попадает в commit
- [ ] `web/briefs/*.html` не попадают в commit
- [ ] `garmin-morning_1/` исключён
- [ ] README.md с инструкцией запуска
- [ ] `.env.example` без реальных паролей
- [ ] нет личных путей `/Users/...` в документации
