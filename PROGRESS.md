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

## Rozpracováno

- Fáze 4 / Krok 1 — Backend datový základ přes TDD: Vision model, migrace, schémata, routy a `Task.vision_id`.

## Další krok

Napsat failing backend testy pro Vision create/list/detail a `Task.vision_id`, ověřit RED a až potom implementovat model/migraci/službu/routy.

## Poznámky

- Od Fáze 2 platí resumable workflow: každý samostatný krok končí aktualizací tohoto souboru a git commitem.
- Projekt je git repozitář v `/home/zeus/personal-os`, remote `git@github.com:radekpich/personal-os.git`.
- Backend je v `backend/`, frontend ve `frontend/`.
- Backend Fáze 2 je dokončený a ověřený 56 testy + live E2E smoke.
- Fáze 3 dodává každodenně použitelný frontend úkolovníku.
- Fáze 4 přidává modul Visions: strom dlouhodobých cílů + klíčové napojení na úkoly přes `Task.vision_id`.
