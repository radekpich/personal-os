# Personal OS Backend

Phase 1 backend skeleton with async FastAPI, SQLAlchemy 2.0, Alembic and cookie-based JWT authentication.

## Requirements

- Python 3.12 target. The current Hermes VPS has Python 3.11.15, so the code is verified locally on 3.11 while tooling targets Python 3.12.
- SQLite for development via `aiosqlite`; PostgreSQL-ready via `DATABASE_URL`.

## Install

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` and set a real `SECRET_KEY`.

## Database

```bash
. .venv/bin/activate
alembic upgrade head
```

## Create user

No public registration endpoint exists. Create the first account from CLI:

```bash
. .venv/bin/activate
python -m app.cli create-user --email radek@example.com --display-name "Radek Pich"
```

Add `--password '...'` only for local smoke tests; prefer interactive prompt on real systems.

## Run

```bash
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Smoke test

```bash
curl -i http://127.0.0.1:8000/health
```

For login, first read the `csrf_token` cookie from `/health`, then send it back as `X-CSRF-Token` with `/auth/login`. JWTs are delivered only in httpOnly cookies.

## Quality gates

```bash
. .venv/bin/activate
ruff check .
ruff format --check .
mypy --strict app tests
pytest -q
```

## API

- `GET /health`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

There is intentionally no `/auth/register` endpoint.
