# PROGRESS.md — Personal OS

## Aktuální fáze — Fáze 2: Jádro aplikace

## Hotovo

- [x] 2026-09-04 17:?? — Krok 0 — Baseline a pracovní pravidla
  - Vytvořeno/aktualizováno: `PLAN.md`, `PROGRESS.md`, `.gitignore`
  - Ověřeno: backend Fáze 1 prošel `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q`
- [x] 2026-09-04 17:09 — Krok 1 — Uživatelský profil pro calendar token
  - Vytvořeno: `backend/tests/test_calendar_token.py`, `backend/alembic/versions/8f4b2d3a1c6e_add_calendar_token_to_users.py`
  - Upraveno: `backend/app/models/user.py`, `backend/app/schemas/user.py`, `backend/app/core/security.py`
  - Ověřeno: RED test selhal na chybějícím `calendar_token`, poté prošel; kompletní brány prošly; Alembic upgrade na čisté DB prošel; CLI vytvořilo uživatele s tokenem délky 43.

- [x] 2026-09-04 17:15 — Krok 2 — Category a Context CRUD
  - Vytvořeno: `backend/app/models/category.py`, `backend/app/models/context.py`, `backend/app/schemas/category.py`, `backend/app/schemas/context.py`, `backend/app/services/category_service.py`, `backend/app/services/context_service.py`, `backend/app/api/routes/categories.py`, `backend/app/api/routes/contexts.py`, `backend/alembic/versions/0ac9244f77b2_add_categories_and_contexts.py`, `backend/tests/test_categories.py`, `backend/tests/test_contexts.py`
  - Upraveno: `backend/app/models/__init__.py`, `backend/app/main.py`
  - Ověřeno: RED testy selhaly na 404/chybějících modelech; poté prošlo `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q` s 23 testy; Alembic upgrade na čisté DB prošel; HTTP smoke ověřil login, chráněné `/categories`, create/list category/context a soft delete contextu.

## Rozpracováno

- Nic není rozpracováno. Krok 2 je dokončený a projekt je v konzistentním stavu.

## Další krok

Začít krokem 3: přidat `Tag`, minimální `Task` model a M:N vazbu `task_tags` včetně owner-scoped tag endpointů.

## Poznámky

- Od Fáze 2 platí resumable workflow: každý samostatný krok končí aktualizací tohoto souboru a git commitem.
- Projekt je git repozitář v `/home/zeus/personal-os`.
- Backend je v `backend/`.
- Na serveru je Python 3.11.15, projekt targetuje Python 3.12 v `pyproject.toml`.
- Calendar token je neveřejný bearer token uložený na `User.calendar_token`; aktuálně je viditelný v `UserRead`, aby jej později mohl použít chráněný profil/regenerate flow.
