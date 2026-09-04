# PROGRESS.md — Personal OS

## Aktuální fáze — Fáze 2: Jádro aplikace

## Hotovo

- [x] 2026-09-04 17:06 — Krok 0 — Baseline a pracovní pravidla
  - Vytvořeno/aktualizováno: `PLAN.md`, `PROGRESS.md`, `.gitignore`
  - Ověřeno: backend Fáze 1 stále prochází `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q`

## Rozpracováno

- Nic není rozpracováno. Projekt je v konzistentním baseline stavu po Fázi 1 a připravený na doménové rozšíření Fáze 2.

## Další krok

Začít krokem 1: přidat `calendar_token` do modelu `User`, schema a Alembic migraci včetně testu.

## Poznámky

- Od Fáze 2 platí resumable workflow: každý samostatný krok končí aktualizací tohoto souboru a git commitem.
- Projekt je git repozitář v `/home/zeus/personal-os`.
- Backend je v `backend/`.
- Na serveru je Python 3.11.15, projekt targetuje Python 3.12 v `pyproject.toml`.
- `backend/PHASE1_REPORT.md` byl doručovací artefakt a je přesunutý do `.artifacts/`, které se necommituje.
