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

- [x] 2026-09-04 17:19 — Krok 3 — Tag a M:N vazba na Task základ
  - Vytvořeno: `backend/app/models/tag.py`, `backend/app/models/task.py`, `backend/app/schemas/tag.py`, `backend/app/services/tag_service.py`, `backend/app/api/routes/tags.py`, `backend/alembic/versions/b7c84319d5aa_add_tags_tasks_and_task_tags.py`, `backend/tests/test_tags.py`
  - Upraveno: `backend/app/models/__init__.py`, `backend/app/main.py`
  - Ověřeno: RED testy selhaly na 404/chybějících modelech; poté prošlo `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q` s 27 testy; Alembic upgrade na čisté DB prošel; HTTP smoke ověřil chráněné `/tags`, create/list/update/delete.

- [x] 2026-09-04 17:43 — Krok 4 — Task CRUD, quick inbox a filtrování
  - Vytvořeno: `backend/app/schemas/task.py`, `backend/app/services/task_service.py`, `backend/app/api/routes/tasks.py`, `backend/alembic/versions/2f6d4e8c9a31_expand_tasks_for_core_task_management.py`, `backend/tests/test_tasks.py`
  - Upraveno: `backend/app/models/task.py`, `backend/app/models/__init__.py`, `backend/app/main.py`
  - Ověřeno: Claude Code narazil na session limit a nechal necommitnutý stav; Hermes doplnil migraci, opravil SQLite `ALTER COLUMN DROP DEFAULT`, poté prošlo `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q` se 47 testy; Alembic upgrade na čisté DB prošel; HTTP smoke ověřil chráněné `/tasks`, `POST /tasks/quick`, create task s category/context/tag a filtry context/tag/inbox.

- [x] 2026-09-04 17:48 — Krok 5 — Opakované úkoly
  - Vytvořeno: `backend/alembic/versions/7b1d2c5e9f40_add_task_recurrence_fields.py`, `backend/tests/test_recurrence.py`
  - Upraveno: `backend/app/models/task.py`, `backend/app/schemas/task.py`, `backend/app/services/task_service.py`
  - Ověřeno: RED testy selhaly na chybějících recurrence polích/generování; poté prošlo `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q` s 51 testy; Alembic upgrade na čisté DB prošel; HTTP smoke ověřil weekly RRULE a vytvoření další instance po dokončení.

- [x] 2026-09-04 17:52 — Krok 6 — iCalendar feed
  - Vytvořeno: `backend/app/services/calendar_ics_service.py`, `backend/app/api/routes/calendar.py`, `backend/tests/test_calendar_ics.py`
  - Upraveno: `backend/app/main.py`
  - Ověřeno: RED testy selhaly na 404; poté prošlo `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q` s 55 testy; Alembic upgrade na čisté DB prošel; HTTP smoke ověřil veřejný `.ics` feed přes token, VEVENT/VTIMEZONE/RRULE a regeneraci tokenu.

- [x] 2026-09-04 17:57 — Krok 7 — Seed data
  - Vytvořeno: `backend/alembic/versions/91c0a6e7d2b8_seed_default_personal_os_data.py`, `backend/tests/test_seed_data.py`
  - Ověřeno: RED test selhal na chybějícím seed demo ownerovi; poté prošlo `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q` s 56 testy; Alembic upgrade na čisté DB vytvořil demo usera, 6 kategorií, 5 kontextů a 3 úkoly.

- [x] 2026-09-05 05:23 — Krok 8 — Finální audit, dokumentace a kompletní smoke Fáze 2
  - Vytvořeno/upraveno: `backend/README.md`, `PROGRESS.md`
  - Ověřeno: `ruff check .`, `ruff format --check .`, `mypy --strict app tests`, `pytest -q` s 56 testy; Alembic upgrade na čisté DB; CLI create-user; živý E2E smoke přes uvicorn pro auth, category/context/tag, quick task, task CRUD/filter, recurrence next instance, ICS feed a regenerate token.
  - Smoke výsledek: `PHASE2_E2E_SMOKE_OK {'health': 200, 'unauth_tasks': 401, 'login': 200, 'category': 201, 'context': 201, 'tag': 201, 'quick': 201, 'task': 201, 'filtered_total': 1, 'next_due': '2026-09-14', 'ics': 200, 'regen': 200, 'old_token': 404}`

## Rozpracováno

- Nic není rozpracováno. Krok 8 je dokončený a Fáze 2 je uzavřená v konzistentním stavu.

## Další krok

Fáze 2 je hotová. Další práce má začít novou fází podle navazujícího plánu.

## Poznámky

- Od Fáze 2 platí resumable workflow: každý samostatný krok končí aktualizací tohoto souboru a git commitem.
- Projekt je git repozitář v `/home/zeus/personal-os`.
- Backend je v `backend/`.
- Na serveru je Python 3.11.15, projekt targetuje Python 3.12 v `pyproject.toml`.
- Calendar token je neveřejný bearer token uložený na `User.calendar_token`; aktuálně je viditelný v `UserRead`, aby jej později mohl použít chráněný profil/regenerate flow.
