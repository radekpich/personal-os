# Personal OS Backend — Phase 1

## Non-negotiable requirements
- Python target: 3.12. Local Hermes host may only have Python 3.11; keep syntax compatible unless explicitly impossible, but set project metadata/mypy/ruff target to py312.
- FastAPI async backend.
- SQLAlchemy 2.0 async only, using modern declarative style: `Mapped[...]` and `mapped_column(...)`. Never use legacy `Column`.
- SQLite with `aiosqlite`, code prepared for PostgreSQL through `DATABASE_URL`.
- Use `sa.Uuid` for UUID columns so PostgreSQL maps natively.
- Alembic configured from the start, including the first migration.
- Pydantic v2 and pydantic-settings `BaseSettings`, config from `.env`; provide `.env.example` with all keys and comments.
- Exact pinned versions in `requirements.txt`; no version ranges.
- Code must pass `ruff check`, `ruff format --check`, `mypy --strict`, and `pytest`.
- Direct `bcrypt` library only. Do not use passlib.
- Auth uses httpOnly cookies only; do not return JWTs in JSON and never design for localStorage.
- No public registration endpoint. Users are created only via `python -m app.cli create-user`.

## Models for Phase 1
### User
- id: UUID primary key
- email
- hashed_password
- display_name
- timezone default `Europe/Prague`
- is_active
- created_at
- updated_at

### RefreshToken
- id: UUID primary key
- user_id
- family_id
- token_hash
- expires_at
- revoked_at
- created_at
- updated_at

## Auth endpoints
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /health`

## Token/cookie behavior
- Access token lifetime: 15 minutes.
- Refresh token lifetime: 30 days.
- Both sent as httpOnly cookies with Secure and SameSite=Lax.
- Implement refresh token rotation: each refresh issues a new refresh token and revokes the old one.
- Store only a hash of refresh token in DB.
- If an already revoked refresh token is used again, treat as token theft and revoke the whole `family_id`.
- Add double-submit CSRF protection for state-changing auth endpoints using a readable CSRF cookie and matching header.

## Security
- CORS from config only, never `*`.
- slowapi rate limiting:
  - `/auth/login`: 5/minute per IP.
  - global default looser from config.
  - in-memory is acceptable because production target is one uvicorn worker.
- Security headers middleware.
- Global exception handler never returns stack traces to the client.
- Structured logging to stdout.

## Tests
- pytest + httpx with in-memory SQLite.
- Cover login success.
- Cover bad password.
- Cover access without token.
- Cover refresh and token rotation.
- Cover reuse of revoked refresh token revoking whole family.
- Cover CSRF enforcement where relevant.

## Architecture
Use modules: `core`, `db`, `models`, `schemas`, `api`, `services`. Keep repository layer out unless query logic is non-trivial. For Phase 1, services may use `AsyncSession` directly.
