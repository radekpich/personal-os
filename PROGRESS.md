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

## Rozpracováno

- Nic není rozpracováno. Krok 1 je dokončený a projekt je v konzistentním stavu.

## Další krok

Začít krokem 2: přidat owner-scoped `Category` a `Context` modely, schémata, services, endpointy, migraci a testy.

## Poznámky

- Od Fáze 2 platí resumable workflow: každý samostatný krok končí aktualizací tohoto souboru a git commitem.
- Projekt je git repozitář v `/home/zeus/personal-os`.
- Backend je v `backend/`.
- Na serveru je Python 3.11.15, projekt targetuje Python 3.12 v `pyproject.toml`.
- Calendar token je neveřejný bearer token uložený na `User.calendar_token`; aktuálně je viditelný v `UserRead`, aby jej později mohl použít chráněný profil/regenerate flow.
