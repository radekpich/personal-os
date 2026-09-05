# Personal OS Backend

Async FastAPI backend pro Personal OS. Stav po Fázi 2: cookie-based JWT auth, owner-scoped kategorie/kontexty/tagy, úkoly s filtry, opakování přes RRULE, veřejný read-only iCalendar feed a seed data.

## Requirements

- Python 3.12 target. Aktuální Hermes VPS má Python 3.11.15, kód je lokálně ověřený i na 3.11.
- SQLite pro development přes `aiosqlite`; PostgreSQL-ready přes `DATABASE_URL`.

## Install

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

V `.env` nastav reálný `SECRET_KEY`.

## Database

```bash
. .venv/bin/activate
alembic upgrade head
```

Migrace Fáze 2 přidávají:

- `users.calendar_token`
- `categories`, `contexts`, `tags`
- `tasks`, `task_tags`
- recurrence fields na `tasks`
- demo seed ownera `seed-demo@personal-os.local` s výchozími kategoriemi, kontexty a ukázkovými úkoly

## Create user

Veřejná registrace záměrně neexistuje. První účet vytvoř přes CLI:

```bash
. .venv/bin/activate
python -m app.cli create-user --email radek@example.com --display-name "Radek Pich"
```

`--password '...'` používej jen pro lokální smoke testy; na reálném systému preferuj interaktivní prompt.

## Run

```bash
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Auth a CSRF

Pro login nejdřív načti `csrf_token` cookie z `/health`, pak ji pošli zpět jako `X-CSRF-Token` na `/auth/login`. JWT se posílají pouze jako httpOnly cookies.

Mutace chráněných zdrojů vyžadují:

- přihlášeného uživatele
- CSRF hlavičku `X-CSRF-Token`

## Quality gates

```bash
. .venv/bin/activate
ruff check .
ruff format --check .
mypy --strict app tests
pytest -q
```

## API přehled

### Health / auth

| Method | Path | Poznámka |
|---|---|---|
| `GET` | `/health` | healthcheck + CSRF cookie |
| `POST` | `/auth/login` | cookie login |
| `POST` | `/auth/refresh` | refresh access tokenu |
| `POST` | `/auth/logout` | revoke refresh family |
| `GET` | `/auth/me` | aktuální uživatel včetně `calendar_token` |

Registrace není záměrně dostupná.

### Kategorie, kontexty, tagy

| Resource | Endpointy |
|---|---|
| Kategorie | `GET/POST /categories`, `GET/PATCH/DELETE /categories/{id}` |
| Kontexty | `GET/POST /contexts`, `GET/PATCH/DELETE /contexts/{id}` |
| Tagy | `GET/POST /tags`, `GET/PATCH/DELETE /tags/{id}` |

Vše je owner-scoped. Delete je soft delete.

### Úkoly

| Method | Path | Poznámka |
|---|---|---|
| `POST` | `/tasks/quick` | rychlý inbox task jen z titulku |
| `GET` | `/tasks` | stránkovaný seznam s filtry |
| `POST` | `/tasks` | vytvoření úkolu |
| `GET` | `/tasks/{id}` | detail |
| `PATCH` | `/tasks/{id}` | update / dokončení |
| `DELETE` | `/tasks/{id}` | soft delete |

Podporované query filtry na `GET /tasks`:

- `status`
- `priority`
- `category_id`
- `context_id`
- `tag_id`
- `due_from`
- `due_to`
- `q`
- `view=today|this_week|overdue|inbox`
- `limit`, `offset`

### Opakované úkoly

Task podporuje:

- `recurrence_rule` — RRULE string, např. `FREQ=WEEKLY;BYDAY=MO`
- `recurrence_mode` — `fixed` nebo `after_completion`
- `recurrence_template_id` — vyplní se na dalších instancích

Při přechodu úkolu do `done` se vygeneruje další aktivní instance, pokud úkol má recurrence nastavení.

### Calendar feed

| Method | Path | Poznámka |
|---|---|---|
| `GET` | `/calendar/{token}.ics` | veřejný read-only iCalendar feed podle `users.calendar_token` |
| `POST` | `/calendar/regenerate-token` | chráněná regenerace tokenu |

ICS feed:

- exportuje úkoly s `due_date` jako `VEVENT`
- obsahuje `VTIMEZONE:Europe/Prague`
- pro recurrence tasky exportuje `RRULE`
- neexportuje privátní description text
- vrací `Cache-Control: no-store`

## Lokální E2E smoke flow

```bash
rm -f /tmp/personal_os.db
export DATABASE_URL=sqlite+aiosqlite:////tmp/personal_os.db
export SECRET_KEY=local-smoke-secret-key
export CORS_ORIGINS=http://localhost:3000
export COOKIE_SECURE=false
export ENVIRONMENT=test
export ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=15
export REFRESH_TOKEN_EXPIRE_DAYS=30
export ACCESS_COOKIE_NAME=access_token
export REFRESH_COOKIE_NAME=refresh_token
export CSRF_COOKIE_NAME=csrf_token
export CSRF_HEADER_NAME=X-CSRF-Token
export RATE_LIMIT_LOGIN=5/minute
export RATE_LIMIT_DEFAULT=100/minute

. .venv/bin/activate
alembic upgrade head
python -m app.cli create-user \
  --email smoke@example.com \
  --display-name "Smoke User" \
  --password 'CorrectHorseBatteryStaple123!'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Pak z klienta ověř:

1. `GET /health`
2. `POST /auth/login` s CSRF
3. `POST /categories`, `/contexts`, `/tags`
4. `POST /tasks/quick`
5. `POST /tasks` s category/context/tag a recurrence
6. `PATCH /tasks/{id}` na `done` a ověř další instanci
7. `GET /calendar/{token}.ics`
8. `POST /calendar/regenerate-token`
