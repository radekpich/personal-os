# PROGRESS.md — Personal OS

## Aktuální fáze — Fáze 4: Modul dlouhodobých cílů / Visions

## Hotovo

- [x] 2026-09-05 07:17 — Fáze 4 / Krok 0 — Plán a baseline
  - Zapsána Fáze 4 do `PLAN.md`.
  - Založen pracovní checklist pro backend model/strom/progress a frontend stromový modul.
  - Ověřen stav repozitáře: čistý pracovní strom, lokálně `main` ahead proti `origin/main` o 2 commity z Fáze 3.
  - Ověřena existující architektura backendu: modely/schémata/služby/routy pro tasks/categories/contexts/tags.
  - Ověřena existující architektura frontendu: typed API klient, hooks, AppShell, task detail panel.

### Fáze 3 — Frontend použitelný pro každodenní práci

- [x] 2026-09-05 06:15 — Fáze 3 / Krok 1–7 — Frontend každodenního úkolovníku
  - Vytvořeno: použitelný frontend v `frontend/` nad backendem Fáze 2.
  - Stack: Next.js `15.5.7`, App Router, TypeScript strict, Tailwind CSS v4, Radix/shadcn styl komponent.
  - Design: všechny základní barvy, typografie, radiusy, spacing a stíny jako CSS proměnné v `frontend/src/app/globals.css`; light/dark přes `next-themes`.
  - Datová vrstva: ručně psaný typed API klient podle backend kontraktu, `credentials: 'include'`, CSRF helper, refresh po 401, TanStack Query hooks.
  - Auth: login přes httpOnly cookie backend, Next middleware chrání privátní routy a pouští refresh-cookie session, AppShell redirectuje na login při neobnovitelné 401.
  - Layout: sidebar s pohledy/kategoriemi, mobilní bottom nav od 375px, quick capture vždy nahoře.
  - Obrazovky: Dashboard, Úkoly s filtry, Inbox, Settings s profilem/timezone a calendar URL copy/regenerate.
  - Úkoly: quick create bez modálu, seznam, detail v side panelu, RHF+Zod formulář, optimistic done toggle.
  - Command palette: Cmd/Ctrl+K, hledání úkolů, skoky do pohledů/kategorií, založení úkolu; další zkratky Cmd/Ctrl+N a Cmd/Ctrl+1–4.
  - PWA: manifest, ikony 192/512, service worker jen pro statické assety.
  - Ověřeno frontend: `npm run lint`, `npm run typecheck`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:53901 npm run build`.
  - Ověřeno backend: `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q` → 56 passed.
  - Ověřeno E2E: produkční `next start` + backend uvicorn + `npm run phase3:smoke`.

- [x] 2026-09-05 05:37 — Fáze 3 / Krok 0 — Frontend skeleton a plán
  - Vytvořeno/upraveno: `frontend/`, `PLAN.md`, `PROGRESS.md`.
  - Ověřeno: `npm run lint`, `npm run typecheck`, `npm run build`.

### Fáze 2 — Jádro aplikace

- [x] Krok 0 — Baseline a pracovní pravidla
- [x] Krok 1 — Uživatelský profil pro calendar token
- [x] Krok 2 — Category a Context CRUD
- [x] Krok 3 — Tag a M:N vazba na Task základ
- [x] Krok 4 — Task CRUD, quick inbox a filtrování
- [x] Krok 5 — Opakované úkoly
- [x] Krok 6 — iCalendar feed
- [x] Krok 7 — Seed data
- [x] Krok 8 — Finální audit, dokumentace a kompletní smoke Fáze 2

- [x] 2026-09-05 07:24 — Fáze 4 / Krok 1 — Backend datový základ přes TDD
  - Přidán `Vision` model s poli `title`, Markdown `description`, `parent_id`, `horizon`, `status`, `target_date`, `category_id`, `position` a audit/soft-delete sloupci.
  - Přidány enumy `VisionHorizon` (`life`, `5y`, `1y`, `quarter`) a `VisionStatus` (`active`, `paused`, `achieved`, `abandoned`).
  - Přidána migrace `d4b8f72c9e11_add_visions_and_task_vision_link.py`.
  - Přidán `Task.vision_id` s FK `visions.id ON DELETE SET NULL` do modelu, schémat a service vrstvy.
  - Přidány základní `/visions` endpointy: list/create/get/patch/delete.
  - TDD RED ověřeno: `pytest tests/test_visions.py -q` nejdřív padal na chybějících endpointech a ignorovaném `vision_id`.
  - GREEN ověřeno: `pytest tests/test_visions.py -q` → 4 passed.
  - Ověřeno slice gates: `ruff check app tests/test_visions.py`, `ruff format --check app tests/test_visions.py`, `mypy --strict app tests/test_visions.py`.
  - Ověřeno Alembic na čerstvé SQLite DB: tabulka `visions` existuje a `tasks.vision_id` existuje.

- [x] 2026-09-05 07:31 — Fáze 4 / Krok 2–3 — Backend strom, progress a stagnace
  - Přidána ochrana Vision stromu: self-parent → 400, cyklus → 400, cizí/neexistující parent → 404, max hloubka 4 úrovně → 400.
  - Přidán `GET /visions/tree`, skládá celý strom z jednoho selectu nad `visions` a nedělá N+1.
  - Přidán `GET /visions/{id}/progress`: `total_tasks`, `done_tasks`, `last_activity_at`, `stagnation_days`.
  - Přidán `GET /visions/stagnating?days=X`: vrací vize bez posledního pohybu na navázaných úkolech aspoň X dní.
  - TDD RED ověřeno pro stromové validace, tree route i progress/stagnating endpointy.
  - GREEN ověřeno: `pytest tests/test_visions.py -q` → 10 passed.
  - Backend gates ověřeny: `ruff check .`, `ruff format --check .`, `mypy --strict app tests`, `pytest -q` → 66 passed.

## Rozpracováno

- Fáze 4 / Krok 4 — Frontend API typy/hooks pro vize a `Task.vision_id`.

## Další krok

Doplnit frontend typy, API metody a TanStack Query hooks pro Vision tree/progress/stagnating a upravit Task typ/form payload o `vision_id`.

## Poznámky

- Od Fáze 2 platí resumable workflow: každý samostatný krok končí aktualizací tohoto souboru a git commitem.
- Projekt je git repozitář v `/home/zeus/personal-os`, remote `git@github.com:radekpich/personal-os.git`.
- Backend je v `backend/`, frontend ve `frontend/`.
- Backend Fáze 2 je dokončený a ověřený 56 testy + live E2E smoke.
- Fáze 3 dodává každodenně použitelný frontend úkolovníku.
- Fáze 4 přidává modul Visions: strom dlouhodobých cílů + klíčové napojení na úkoly přes `Task.vision_id`.
