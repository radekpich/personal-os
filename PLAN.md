# PLAN.md — Personal OS

## Fáze 3 — Frontend použitelný pro každodenní práci

Cíl: postavit použitelný frontend úkolovníku nad hotovým backendem Fáze 2.

### Technický základ

- Next.js 15, App Router, TypeScript strict.
- Tailwind CSS v4.
- shadcn/ui styl komponent: Radix primitives + `cn`, varianty přes `class-variance-authority`.
- Design tokeny centralizované v jednom souboru `frontend/src/app/globals.css` jako CSS proměnné: barvy, radiusy, spacing, fonty, stíny.
- Light/dark přes `next-themes`.
- TanStack Query pro server state.
- Typovaný API klient podle backend OpenAPI kontraktu / ručně udržované typy.
- Formuláře přes `react-hook-form` + `zod`.
- PWA manifest, ikony, standalone mode, SW pouze pro statické assety.

### Kroky

1. **Krok 0 — Frontend skeleton a plán**
   - Next app v `frontend/`, Next 15, TypeScript strict, Tailwind v4.
   - Fáze 3 zapsaná do `PLAN.md` a `PROGRESS.md`.
   - Build/lint/typecheck projdou.

2. **Krok 1 — API a auth vrstva**
   - `credentials: 'include'` pro všechny requesty.
   - typed API client pro auth, category, context, tag, task, calendar.
   - automatický refresh po 401 a router redirect na login.
   - TanStack Query provider a query/mutation hooks.

3. **Krok 2 — Design system a shell**
   - Theme provider, light/dark toggle.
   - App shell se sidebar pohledy/kategoriemi a mobile bottom nav od 375 px.
   - Middleware chrání privátní routy.

4. **Krok 3 — Dashboard, úkoly a inbox**
   - Dashboard: dnešní úkoly, po termínu, rychlý přehled.
   - List úkolů s filtry category/context/tag/status.
   - Inbox pro nekategorizované položky.
   - Vždy dostupný quick capture nahoře.
   - Optimistické zaškrtnutí úkolu.

5. **Krok 4 — Detail úkolu a formuláře**
   - Detail v postranním panelu, ne samostatná stránka.
   - Create/update task přes RHF + Zod.
   - Validace priority, status, termín, recurrence, tagy.

6. **Krok 5 — Nastavení**
   - Profil a timezone.
   - Calendar URL, kopírování do schránky, regenerace tokenu.

7. **Krok 6 — Command palette, klávesové zkratky, PWA**
   - Cmd/Ctrl+K palette: vyhledání úkolu, skok do kategorie, založení úkolu.
   - Zkratky pro quick capture, inbox, today/list/settings, theme.
   - Manifest, ikony, service worker pouze statické assety.

8. **Krok 7 — Finální smoke a push**
   - `npm run lint`, `npm run typecheck`, `npm run build`.
   - Backend + frontend live E2E smoke.
   - Browser visual smoke desktop/mobile a console bez chyb.
   - Commit + push.

### UX zásady

- Klidné minimalistické rozhraní, hodně bílého prostoru.
- Barva jen tam, kde nese informaci: kategorie, priorita, po splatnosti.
- Rychlý zápis bez modálu a povinných polí: text → Enter → hotovo → pole prázdné.
- Detail úkolu je panel/drawer; běžná práce zůstává v seznamu.
- Mobil od 375 px: žádné horizontálně rozbité layouty, spodní navigace, velké touch targety.
