# PLAN.md — Personal OS

## Fáze 4 — Modul dlouhodobých cílů / Visions

Cíl: přidat modul dlouhodobých cílů, který propojí sny/cíle/milníky s každodenními úkoly. Bez vazby `Task.vision_id` nejsou vize jádro systému, proto je propojení úkolů na vize součástí backendu i frontendu.

### Datový model

`Vision`:

- `id`, `owner_id`
- `title`
- `description` — Markdown text
- `parent_id` — self-reference strom
- `horizon` — `life`, `5y`, `1y`, `quarter`
- `status` — `active`, `paused`, `achieved`, `abandoned`
- `target_date`
- `category_id`
- `position`
- `created_at`, `updated_at`, `deleted_at`

`Task`:

- přidat volitelné `vision_id` s `ON DELETE SET NULL`

### Stromová pravidla

- Při create/update parenta ověřit, že parent patří stejnému uživateli a není soft-deleted.
- Při změně parenta nesmí vzniknout cyklus.
- Maximální hloubka stromu je 4 úrovně včetně rootu.
- `GET /visions/tree` načte všechny vize uživatele jedním DB dotazem a strom složí v paměti; nesmí dělat N+1.

### API

- `GET /visions` — plochý seznam pro selecty a administraci.
- `POST /visions` — create.
- `GET /visions/{id}` — detail.
- `PATCH /visions/{id}` — update, včetně přesunu parenta/position.
- `DELETE /visions/{id}` — soft delete; děti přepojit na parenta nebo root podle jednoduchého YAGNI pravidla.
- `GET /visions/tree` — celý strom.
- `GET /visions/{id}/progress` — počet navázaných úkolů, počet hotových, datum posledního pohybu, počet dní stagnace.
- `GET /visions/stagnating?days=X` — vize, na kterých se X dní nic nestalo.

### Frontend

- Nová navigace `Vize` / `/visions`.
- Stromový pohled:
  - rozbalování/sbalování,
  - drag & drop přesouvání v hierarchii,
  - progress bar u každé vize,
  - viditelný ukazatel stagnace.
- Detail vize v panelu:
  - title,
  - Markdown description,
  - horizon,
  - status,
  - target date,
  - category,
  - parent,
  - position.
- Detail úkolu:
  - select `vision_id`, aby šlo každý úkol navázat na dlouhodobý cíl.

### Kroky

1. **Krok 0 — Plán a baseline**
   - Zapsat Fázi 4 do `PLAN.md` a `PROGRESS.md`.
   - Ověřit čistý repo stav a existující architekturu.
   - Commit `faze-4/krok-0: plan modulu vizi`.

2. **Krok 1 — Backend datový základ přes TDD**
   - Testy pro Vision create/read/list a `Task.vision_id`.
   - Model `Vision`, enumy, schémata, migrace.
   - Doplnit `Task.vision_id` do modelu, schémat a služby.
   - Ověřit Alembic upgrade čerstvé SQLite DB.
   - Commit `faze-4/krok-1: datovy model vizi`.

3. **Krok 2 — Strom a ochrana integrity**
   - Testy cyklu, self-parent, cizí parent, hloubka >4.
   - Implementovat parent validaci ve `vision_service`.
   - `GET /visions/tree` skládá strom z jednoho selectu.
   - Commit `faze-4/krok-2: strom vizi a ochrany`.

4. **Krok 3 — Progress a stagnace**
   - Testy pro progress nad linked tasks.
   - `last_movement_at` = max z `Vision.updated_at` a `Task.updated_at` pro navázané úkoly.
   - `stagnation_days` = rozdíl dneška a `last_movement_at` v Europe/Prague / UTC-safe režimu.
   - `GET /visions/stagnating?days=X` vrací aktivní/paused vize bez pohybu alespoň X dní.
   - Commit `faze-4/krok-3: progress a stagnace vizi`.

5. **Krok 4 — Frontend API vrstva**
   - Doplnit Vision typy, API klient a TanStack hooks.
   - Doplnit `vision_id` do Task typů/create/update.
   - Commit `faze-4/krok-4: frontend api pro vize`.

6. **Krok 5 — Frontend stromový modul**
   - Nová route `/visions` a navigace v AppShell.
   - Tree view s lokálním expanded stavem.
   - DnD přes `@dnd-kit/*` nebo nativní drag/drop, podle jednoduchosti a stability.
   - Progress bar a stagnation badge u každé položky.
   - Detail panel pro editaci vize.
   - Commit `faze-4/krok-5: stromovy frontend vizi`.

7. **Krok 6 — Propojení úkolů s vizemi**
   - Select v detail panelu úkolu.
   - List/command UX ukáže navázanou vizi tam, kde to dává smysl.
   - Commit `faze-4/krok-6: propojeni ukolu s vizemi`.

8. **Krok 7 — Smoke, dokumentace, push**
   - Backend: `ruff check`, `ruff format --check`, `mypy --strict app tests`, `pytest -q`.
   - Frontend: `npm run lint`, `npm run typecheck`, `NEXT_PUBLIC_API_BASE_URL=... npm run build`.
   - Live E2E smoke: create vision tree, move node přes DnD/API, attach task to vision, progress/stagnating visible.
   - Mobile 375px visual smoke.
   - Aktualizovat `PROGRESS.md`, commit a push.

### UX zásady

- Vize nejsou jen seznam přání — každá obrazovka musí podporovat otázku „co jsem pro to udělal naposledy?“.
- Ukazatel stagnace musí být viditelný i bez otevření detailu.
- Strom max 4 úrovně drží mentální model: sen → cíl → milník → krok/skupina.
- Drag & drop musí respektovat backend validaci; frontend může preventivně blokovat zjevně neplatné přesuny, ale zdrojem pravdy je backend.

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

1. **Krok 0 — Frontend skeleton a plán** — hotovo.
2. **Krok 1 — API a auth vrstva** — hotovo.
3. **Krok 2 — Design system a shell** — hotovo.
4. **Krok 3 — Dashboard, úkoly a inbox** — hotovo.
5. **Krok 4 — Detail úkolu a formuláře** — hotovo.
6. **Krok 5 — Nastavení** — hotovo.
7. **Krok 6 — Command palette, klávesové zkratky, PWA** — hotovo.
8. **Krok 7 — Finální smoke a push** — hotovo lokálně, push zůstává k potvrzení.

### UX zásady

- Klidné minimalistické rozhraní, hodně bílého prostoru.
- Barva jen tam, kde nese informaci: kategorie, priorita, po splatnosti.
- Rychlý zápis bez modálu a povinných polí: text → Enter → hotovo → pole prázdné.
- Detail úkolu je panel/drawer; běžná práce zůstává v seznamu.
- Mobil od 375 px: žádné horizontálně rozbité layouty, spodní navigace, velké touch targety.
