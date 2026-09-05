# PLAN.md — Personal OS

## Fáze 6A — Univerzální subsystém příloh / Attachments

Cíl: přidat bezpečný a znovupoužitelný subsystém pro nahrávání souborů, který teď použijí úkoly a později deník/poznámky i další entity. Binární data jsou vždy na disku, metadata v DB. Model přílohy zůstává univerzální; vazba na entity se dělá přes konkrétní spojovací tabulky, ne přes polymorfní `entity_type + entity_id`.

### Datový model

`Attachment`:

- `id`, `owner_id`
- `storage_path`, `thumbnail_path`
- `original_filename`, `mime_type`, `size_bytes`
- `width`, `height`
- `checksum_sha256`
- `captured_at` — z EXIF `DateTimeOriginal`, pokud existuje
- `gps_lat`, `gps_lon` — z EXIF GPS, pokud existuje
- `caption`
- `processing_status` — `pending`, `ready`, `failed`
- `created_at`, `deleted_at`

Spojovací tabulky:

- `task_attachments(task_id, attachment_id, position)` — reálně používané v části A.
- `note_attachments(note_id, attachment_id, position)` — připravený vzor pro část B; bez polymorfních klíčů.

### Storage pravidla

- Soubory se ukládají do `{ATTACHMENTS_DIR}/{owner_id}/{YYYY}/{MM}/{uuid}.{ext}`.
- Cesta se generuje na serveru z UUID, nikdy z klientského názvu souboru.
- Binární data nikdy nejdou do SQLite.
- Zápis je atomický: stream do dočasného souboru, potom `os.replace`.
- Limit jednoho uploadu je konfigurovatelný (`MAX_ATTACHMENT_SIZE_MB`, default 15 MB) a kontroluje se při streamování.
- Celkový limit je konfigurovatelný (`MAX_STORAGE_MB`); upload se odmítne před finálním uložením s jasnou chybou.
- Povolené typy se ověřují podle magic bytes: JPEG, PNG, HEIC, WebP, PDF. Nepoužívat příponu ani `Content-Type` od klienta jako zdroj pravdy.
- `checksum_sha256` slouží k deduplikaci fyzických souborů: stejný obsah se fyzicky neuloží dvakrát, jen vznikne další metadata/vazba.

### Processing

- Processing běží mimo request přes `BackgroundTasks`; upload vrací rychle se stavem `pending`.
- Obrázky:
  - načíst přes Pillow / pillow-heif,
  - aplikovat EXIF Orientation,
  - před odstraněním EXIF vytáhnout `DateTimeOriginal` a GPS,
  - delší hranu zmenšit na max 2000 px,
  - uložit jako JPEG kvalita 85 bez EXIF,
  - vytvořit náhled s delší hranou 400 px.
- HEIC převést na JPEG.
- PDF nekomprimovat, uložit originál; vytvořit náhled první stránky.
- `processing_status`: `pending → ready` nebo `failed`.

### API

- `POST /attachments` — multipart upload, vrací metadata včetně `processing_status`.
- `GET /attachments/{id}` — chráněné přihlášením a kontrolou vlastníka, stream souboru z backendu.
- `GET /attachments/{id}/thumb` — chráněný thumbnail stream.
- `PATCH /attachments/{id}` — úprava `caption`.
- `DELETE /attachments/{id}` — soft delete; fyzický úklid až po 30 dnech.
- `POST /tasks/{id}/attachments` — napojení attachmentu na task s `position`.
- `DELETE /tasks/{id}/attachments/{attachment_id}` — odebrání vazby.
- `GET /storage/usage` — počet souborů, obsazeno, zbývá, procenta.

Bezpečnost:

- Přístup k cizí příloze vrací 404, ne 403.
- Přílohy neservírovat jako veřejné statické soubory.
- Zakázané typy, path traversal názvy, překročení per-file limitu i storage limitu mají testy.

### Cleanup

- Denní APScheduler/Background úloha smaže fyzické soubory u attachmentů soft-deleted před více než 30 dny.
- Stejná úloha najde osiřelé fyzické soubory bez DB záznamu a odstraní je.

### Frontend

- Znovupoužitelná upload komponenta:
  - drag & drop,
  - výběr souboru,
  - fotoaparát přes `<input type="file" accept="image/*" capture="environment">`,
  - progress stav,
  - mřížka thumbnailů,
  - lightbox.
- V detailu úkolu sekce „Přílohy“ s uploadem a odebráním vazby.
- V nastavení karta obsazenosti úložiště z `GET /storage/usage`.

### Kroky

1. **Krok 0 — Plán a baseline**
   - Zapsat Fázi 6A do `PLAN.md`/`PROGRESS.md`.
   - Ověřit čistý `main` po Fázi 5.
   - Commit `faze-6a/krok-0: plan priloh`.

2. **Krok 1 — Backend datový model a config přes TDD**
   - RED testy migrace/modelu pro `attachments`, `task_attachments`, `note_attachments` a storage config defaulty.
   - Modely, enum, migrace, settings a `.env.example`.
   - Fresh Alembic upgrade.
   - Commit `faze-6a/krok-1: datovy model priloh`.

3. **Krok 2 — Upload a bezpečnostní validace přes TDD**
   - RED testy: povolený typ, zakázaný typ, path traversal filename, per-file limit streamem, storage limit, cizí příloha 404, dedupe stejného souboru.
   - Implementovat `POST /attachments`, magic bytes, atomický zápis, checksum dedupe, `GET /storage/usage`.
   - Commit `faze-6a/krok-2: upload priloh a limity`.

4. **Krok 3 — Processing obrázků/PDF mimo request**
   - RED/GREEN testy pro thumbnail, JPEG normalizaci, EXIF orientation/metadata, HEIC převod pokud knihovna dostupná, PDF thumbnail.
   - BackgroundTasks processing a status transitions.
   - Commit `faze-6a/krok-3: processing priloh`.

5. **Krok 4 — Entity vazby a serving**
   - `GET /attachments/{id}`, `/thumb`, `PATCH`, `DELETE`, `POST/DELETE /tasks/{id}/attachments`.
   - Cleanup úloha pro soft-deleted a orphan soubory.
   - Commit `faze-6a/krok-4: endpointy a vazby priloh`.

6. **Krok 5 — Frontend API a reusable uploader**
   - Typy, API client, hooks, upload component, thumbnail grid a lightbox.
   - Commit `faze-6a/krok-5: frontend upload komponenta`.

7. **Krok 6 — Task detail a storage settings**
   - Přílohy v detailu úkolu, storage usage v Settings.
   - Commit `faze-6a/krok-6: prilohy v ukolech a storage`.

8. **Krok 7 — Smoke, dokumentace, push**
   - Backend/frontend gates a produkční E2E smoke: upload obrázku k úkolu, thumbnail, lightbox, delete link, storage usage.
   - Aktualizovat `PROGRESS.md`, commit a push.

## Fáze 5 — Měření návyků / Challenges

Cíl: přidat modul měření návyků, který zvládá dva odlišné typy šňůr bez společné zkratkové logiky: `daily_action` vyžaduje aktivní zápis, `abstinence` automaticky běží od startu/posledního relapsu. Všechny hranice dnů se počítají podle timezone uživatele (`User.timezone`, typicky `Europe/Prague`), ne podle UTC serveru.

### Datový model

`Challenge`:

- `id`, `owner_id`
- `title`
- `description`
- `type` — `daily_action`, `abstinence`
- `category_id`
- `vision_id`
- `started_at` — timezone-aware datetime začátku výzvy
- `target_days` — volitelný cíl
- `allowed_gap_days` — grace period pro `daily_action`, default 0
- `is_active`
- `color`
- `icon`
- `current_streak`, `longest_streak`
- `created_at`, `updated_at`, `deleted_at`

`CheckIn`:

- `id`, `owner_id`, `challenge_id`
- `date` — lokální datum uživatele, unikátní pro `(challenge_id, date)`
- `value` — volitelné číslo
- `note`
- `is_relapse`
- `created_at`, `updated_at`

`ChallengePause`:

- `id`, `owner_id`, `challenge_id`
- `start_date`, `end_date`
- `note`

### Kritická pravidla

- Timezone: pokud klient neposílá `date`, backend určí dnešní den z aktuálního času v `User.timezone`. UTC server nesmí rozhodovat hranici dne.
- Zpětný zápis: `CheckIn.date` může být max 7 lokálních dní zpět; budoucnost odmítnout.
- Idempotence: opakovaný zápis stejného dne a výzvy provede upsert, ne duplikát; vrací přepočtené streaky.
- `daily_action`: úspěšné dny jsou check-iny s `is_relapse=false`; šňůra se počítá jen z existujících zápisů, ale `allowed_gap_days` toleruje mezery. Pauzy se do přerušení nepočítají.
- `abstinence`: úspěch se nezapisuje; zapisuje se jen relaps (`is_relapse=true`). Current streak = lokální dny od `started_at` nebo posledního relapsu, s pauzami odečtenými/ignorovanými podle lokálního kalendáře. `allowed_gap_days` se na abstinence nevztahuje.
- Nedělat jednu sdílenou funkci pro oba typy; service má oddělené výpočty pro daily_action a abstinence.

### API

- `GET /challenges` — seznam challenge karet se základními streaky.
- `POST /challenges` — create.
- `GET /challenges/{id}` — detail.
- `PATCH /challenges/{id}` — update/freeze přes `is_active` a metadata.
- `DELETE /challenges/{id}` — soft delete.
- `POST /challenges/{id}/check-in` — upsert check-inu, přepočítá a vrátí `current_streak`, `longest_streak`.
- `POST /challenges/{id}/pauses` — založí pauzu.
- `GET /challenges/{id}/stats` — aktuální šňůra, rekord, celkový počet, úspěšnost za 30/90 dní.
- `GET /challenges/{id}/heatmap?year=` — data pro roční 53×7 kalendářovou mřížku.

### Frontend

- Nová navigace `Návyky` / `/challenges`.
- Challenge karta:
  - title, icon, barva,
  - velké číslo current streak,
  - record/target,
  - one-tap dnešní check-in pro `daily_action`, relaps button pro `abstinence`.
- Heatmapa ve stylu GitHub contributions:
  - 53 sloupců × 7 dní,
  - intenzita podle `value`, binárně když `value` chybí,
  - tooltip s datem, hodnotou a poznámkou,
  - na mobilu horizontální scroll.
- Formulář musí umožnit zpětný zápis dne v limitu 7 dní.

### Kroky

1. **Krok 0 — Plán a baseline**
   - Zapsat Fázi 5 do `PLAN.md` a `PROGRESS.md`.
   - Ověřit čistý repo stav po Fázi 4.
   - Commit `faze-5/krok-0: plan navyku`.

2. **Krok 1 — Backend datový základ přes TDD**
   - RED testy pro Challenge create/list/read a CheckIn idempotenci na unikátní den.
   - Modely `Challenge`, `CheckIn`, `ChallengePause`, enum `ChallengeType`, migrace.
   - Routy/services/schémata skeleton.
   - Alembic fresh DB ověření.
   - Commit `faze-5/krok-1: datovy model navyku`.

3. **Krok 2 — Daily action výpočty**
   - RED testy: timezone dnešní datum Europe/Prague, backfill limit 7 dní, future date reject, allowed_gap_days, pause interval.
   - Implementovat oddělenou daily_action streak funkci.
   - Commit `faze-5/krok-2: daily action streaky`.

4. **Krok 3 — Abstinence výpočty**
   - RED testy: automatický běh od `started_at`, relaps reset, žádný úspěšný check-in, timezone hranice dne, pauza.
   - Implementovat oddělenou abstinence streak funkci.
   - Commit `faze-5/krok-3: abstinence streaky`.

5. **Krok 4 — Stats a heatmap**
   - RED testy pro stats 30/90 success rate a heatmap rok/tooltip payload.
   - Implementovat `GET /stats` a `GET /heatmap?year=`.
   - Commit `faze-5/krok-4: stats a heatmap navyku`.

6. **Krok 5 — Frontend API vrstva**
   - Typy, klient, TanStack hooks pro challenges/check-ins/stats/heatmap.
   - Commit `faze-5/krok-5: frontend api navyku`.

7. **Krok 6 — Frontend UI**
   - Route `/challenges`, navigace, challenge karty, one-tap check-in/relaps, heatmap 53×7 s mobile scroll.
   - Commit `faze-5/krok-6: frontend navyky heatmapa`.

8. **Krok 7 — Smoke, dokumentace, push**
   - Backend gates, frontend gates, live E2E smoke pro daily_action i abstinence a mobile visual smoke.
   - Aktualizovat `PROGRESS.md`, commit a push.

### UX zásady

- Návyky musí být použitelné jedním klepnutím: běžný den nesmí vyžadovat otevření formuláře.
- Abstinence nesmí uživatele nutit zapisovat úspěch každý den — primární akce je relaps a číslo běží samo.
- Heatmapa je důkaz historie, ne hlavní ovládání; na mobilu se raději scrolluje vodorovně, než aby se buňky zmenšily na nepoužitelné.

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
