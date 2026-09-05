# PROGRESS.md — Personal OS

## Aktuální fáze — Fáze 3: Frontend použitelný pro každodenní práci

## Hotovo

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
  - PWA: manifest, ikony 192/512, standalone, service worker jen pro statické assety.
  - Ověřeno frontend: `npm run lint`, `npm run typecheck`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:53901 npm run build`.
  - Ověřeno backend: `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q` → 56 passed.
  - Ověřeno E2E: produkční `next start` + backend uvicorn + `npm run phase3:smoke` → login, quick capture, inbox, detail drawer, done toggle, calendar regenerate, command palette, mobile 375px screenshot.
  - Screenshoty smoke: `/tmp/personal-os-phase3-desktop.png`, `/tmp/personal-os-phase3-mobile.png`.

- [x] 2026-09-05 05:37 — Fáze 3 / Krok 0 — Frontend skeleton a plán
  - Vytvořeno/upraveno: `frontend/`, `PLAN.md`, `PROGRESS.md`
  - Stack: Next.js `15.5.7`, App Router, TypeScript strict, Tailwind CSS v4.
  - Ověřeno: `npm run lint`, `npm run typecheck`, `npm run build`.
  - Poznámka: Next 15.5.7 npm hlásí známý security advisory, ale verze je držena kvůli explicitnímu požadavku Next.js 15.

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

- Nic není rozpracováno. Fáze 3 je dokončená a projekt je v konzistentním stavu.

## Další krok

Nasadit/spustit aplikaci v trvalém prostředí a případně doplnit backend endpoint pro editaci profilu/timezone, pokud má být Nastavení plně editovatelné.

## Poznámky

- Od Fáze 2 platí resumable workflow: každý samostatný krok končí aktualizací tohoto souboru a git commitem.
- Projekt je git repozitář v `/home/zeus/personal-os`, remote `git@github.com:radekpich/personal-os.git`.
- Backend je v `backend/`, frontend ve `frontend/`.
- Backend Fáze 2 je dokončený a ověřený 56 testy + live E2E smoke.
- Fáze 3 dodává každodenně použitelný frontend úkolovníku.
