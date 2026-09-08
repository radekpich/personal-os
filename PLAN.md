# PLAN.md — Personal OS

## Fáze 8 — Agent observability a kontrolní panel

Cíl: mít v aplikaci jedno read-only místo pro kompletní nastavení a provoz Hermese: kam má přístup, jaké má úlohy, co hlídá, přes jaké kanály komunikuje a co dělal i mimo úkolovník. Aplikace Hermese nespouští ani neřídí; agent sám reportuje snapshoty a běhy. Jediná výjimka je nouzové odebrání agentních API klíčů.

### Část A — AgentAction audit a revert

Dokončeno: viz `PROGRESS.md`. Týká se mutací aplikačních dat přes API key a drží se odděleně od provozní observability.

### Část B — Hermes registry a provozní přehled

#### Kritické principy

- Data jsou oddělená od Aktivity z části A; sdílí jen menu sekci Agent.
- Aplikace nic nespouští ani neřídí, pouze přijímá reporty a zobrazuje read-only přehled.
- Zápisové reporting endpointy vyžadují API key scope `agent:report`.
- Čtení jde přes běžné přihlášení.
- Nikdy neukládat tokeny, klíče ani hesla; pouze název, typ, rozsah a stav přístupu.
- Registry sync je kompletní snapshot a nahrazuje předchozí stav daného agenta.
- `snapshot_hash` je idempotency klíč. Odlišný hash generuje `AgentConfigChange` diff proti předchozí verzi.
- Nepotvrzené nové integrace/úlohy musí být vidět výrazně jako bezpečnostní signál.
- Volitelné čtení config adresáře z disku je za .env přepínačem, read-only; mismatch se snapshotem se zobrazí jako výstraha.

#### Datový model

- `AgentInstance`: name, version, host, started_at, last_heartbeat_at, status, last_error, config_hash.
- `AgentJob`: name, description, schedule, schedule_description, is_enabled, last_run_at, next_run_at, last_status, last_duration_ms, consecutive_failures, run_count, tags.
- `AgentIntegration`: name, kind, scopes, status, last_used_at, error_count, added_at, notes.
- `AgentWatch`: name, description, kind, config_json, schedule, is_active, last_checked_at, last_triggered_at, trigger_count, last_result.
- `AgentChannel`: channel_type, identifier, is_active, last_message_at, message_count_24h, message_count_month.
- `AgentCapability`: name, description, is_enabled, metadata_json.
- `AgentRun`: agent_id, job_id, trigger, summary, detail, status, started_at, finished_at, duration_ms, tokens_used, cost_estimate, error, tags.
- `AgentConfigChange`: timestamp, change_type, target_type, target_name, diff_json, acknowledged_at.
- `AgentRunDailySummary`: denní agregace starých běhů po retention cleanupu.

#### Endpointy

Reporting pod `agent:report`:

- `POST /agent/heartbeat`
- `POST /agent/registry/sync`
- `POST /agent/runs` — přijímá single i batch payload.
- `POST /agent/watches/{id}/report`

Uživatelské:

- `GET /agent/overview`
- `GET /agent/jobs`
- `GET /agent/integrations`
- `GET /agent/watches`
- `GET /agent/channels`
- `GET /agent/runs`
- `GET /agent/config-changes`
- `POST /agent/config-changes/{id}/acknowledge`
- `GET /agent/keys`
- `POST /agent/keys/revoke-all` — nouzově zneplatní všechny agentní klíče okamžitě.

#### Hlídání samotného agenta

Aplikace vyhodnocuje sama:

- Heartbeat nedorazil déle než konfigurovaný interval → `stale` a varování.
- Úloha nespustila v očekávaném čase podle `next_run_at`.
- Úloha selhala vícekrát za sebou.
- Integrace je `error` nebo `expired`.
- Nová integrace nebo úloha není potvrzená v `AgentConfigChange`.

#### Frontend obrazovka

Sekce Agent má záložky:

- Aktivita — existující část A.
- Přehled — stav běží/neběží, poslední heartbeat, aktivní úlohy/integrace, běhy za 24 h, měsíční spotřeba, pruh nepotvrzených změn.
- Úlohy — tabulka se schedule, posledním/příštím během, stavem, úspěšností, filtr na chybující a proklik do historie úlohy.
- Přístupy — karty podle typu, scopes, stav, poslední použití, vizuálně odlišit zápisové scopes a nové položky.
- Hlídání — watches a poslední výsledek.
- Historie — časová osa běhů s filtrem job/trigger/status/date/q a rychlým stránkováním.
- Změny — diff a potvrzení.
- Klíče — prefix, scopes, poslední použití, revokace; nouzový vypínač oddělený potvrzovacím dialogem.

#### Retence

Přidat service/job funkci, která `AgentRun` starší než 90 dní agreguje do denních souhrnů a maže detail. Spouštění každou hodinu může zůstat jako interní callable/CLI připravená pro scheduler.

#### Kroky

1. **Krok 0 — Plán a baseline**
   - Zapsat Fázi 8B do `PLAN.md`/`PROGRESS.md`, ověřit čistý `main`.
2. **Krok 1 — Modely a migrace přes TDD**
   - RED/GREEN pro všechny nové tabulky, enumy, FK a unikátní identitu snapshot prvků.
3. **Krok 2 — Registry sync + diff přes TDD**
   - Idempotentní hash, replace snapshot, diff změn, heartbeat update, stale výpočet.
4. **Krok 3 — Runs/watch reporting + retence přes TDD**
   - Batch `/agent/runs`, watch report, daily aggregation cleanup.
5. **Krok 4 — Read API + emergency revoke-all přes TDD**
   - Overview, listy, filtry, acknowledge, keys view/revoke all.
6. **Krok 5 — Frontend registry panel**
   - Tabs a všechny read-only přehledy, emergency confirm dialog.
7. **Krok 6 — AGENT.md reporting kontrakt**
   - Curl ukázky, kdy posílat heartbeat/sync/runs/watch report, žádné secrety.
8. **Krok 7 — Full gates, produkční E2E smoke a push**
   - Backend/frontend gates, Playwright smoke registry/runs/changes/keys/revoke-all.

## Fáze 7 — Agent bridge, API klíče a bezpečný obousměrný zápis

Cíl: umožnit externímu AI agentovi na stejném serveru obousměrně pracovat s Personal OS bez vlastní AI vrstvy v aplikaci. Agent musí číst kontext/deník/úkoly, zakládat a upravovat záznamy přes strojovou autentizaci, respektovat ruční webové úpravy a nevytvářet kalendářovou smyčku.

### Kritické principy

- Aplikace nemá vlastního bota ani AI vrstvu; agent je samostatný klient API.
- Lidské cookie auth a strojové `X-API-Key` auth jsou oddělené FastAPI dependencies.
- Současný zápis člověk+agent se řeší datově: `version`, `If-Match`, audit původu a fresh-edit guard.
- Všechny zápisové agent endpointy jsou idempotentní 24 hodin přes `idempotency_key`.
- Kalendářový zápis z aplikace je pouze `.ics` feed; Google Calendar zápisy jsou věc agenta.
- `.ics` feed musí nést `UID=personalos-{task_id}@{domain}` a `X-PERSONALOS-TASK-ID`, agent tyto události ignoruje.

### Datový model

`ApiKey`:

- `id`, `owner_id`
- `name`
- `key_hash` — nikdy plain text
- `key_prefix` — prvních 8 znaků pro zobrazení
- `scopes` — seznam/JSON scope hodnot
- `last_used_at`, `expires_at`, `revoked_at`, `created_at`

Scopes:

- `tasks:read`, `tasks:write`
- `journal:read`, `journal:write`
- `streaks:write`
- `visions:read`
- `attachments:write`
- `calendar:read`

Audit a concurrency na relevantních tabulkách:

- `version` integer, default 1, inkrementace při každé změně
- `created_by` enum/string `user | agent`
- `updated_by` enum/string `user | agent`
- `api_key_id` nullable FK na `api_keys.id`
- task externí reference: `source_system`, `external_id`, `external_updated_at`
- unikátní index nad `(owner_id, source_system, external_id)` pouze pro nenulové externí reference

Relevantní tabulky pro Fázi 7 MVP: `tasks`, `notes`, `challenges/check_ins`, `attachments`.

`IdempotencyKey`:

- `owner_id`, `api_key_id`, `idempotency_key`, `scope`, `request_hash`, `response_body`, `status_code`, `created_at`, `expires_at`
- unique `(api_key_id, idempotency_key)`
- TTL 24 hodin; opakovaný stejný klíč vrací původní výsledek bez duplicity.

### Konflikty a ochrana čerstvých úprav

- `PATCH` a `DELETE` přes agenta i UI posílají `If-Match` s očekávanou verzí.
- Při chybějícím/neshodném `If-Match` vrátit `409 Conflict` s jednotným payloadem:
  - `code`, `message`, `field`, `current`
- Když agent mění záznam, který člověk (`updated_by=user`) upravil v posledním konfigurovatelném intervalu, vrátit `409` s vysvětlením a aktuálním stavem.
- Interval default 5 minut: `AGENT_FRESH_EDIT_GUARD_SECONDS=300`.

### API klíče

- Header `X-API-Key`.
- Samostatná FastAPI dependency pro API klíče vedle cookie auth.
- Vlastní rate limit oddělený od uživatelského: např. `RATE_LIMIT_API_KEY_DEFAULT`.
- CLI:
  - `python -m app.cli create-api-key --email ... --name ... --scopes ... [--expires-at ...]`
  - `python -m app.cli revoke-api-key --prefix ...` nebo `--id ...`
- Klíč zobrazit jen jednou při vytvoření.

### Agent endpointy

- `GET /agent/context` — kategorie, kontexty, aktivní vize, otevřené úkoly, aktuální datum, den v týdnu, timezone; s `ETag`.
- `POST /agent/capture` — hlavní vstup pro `task | note | receipt | idea`; nikdy nezakládá nové kategorie ani kontexty z textu.
- `POST /agent/complete` — dokončení podle ID nebo názvu; při více shodách vrátí kandidáty.
- `POST /agent/checkin` — check-in výzvy.
- `GET /agent/digest?scope=today|week` — kompaktní přehled: dnešní úkoly, po termínu, stav šňůr, stagnující vize.
- `GET /agent/schedule?from=&to=` — úkoly s termínem pro porovnání s kalendářem.
- `PATCH /agent/tasks/{id}/schedule` — agent posune/nastaví termín a čas přes version/If-Match.
- `GET /journal/notes`, `GET /journal/search` — čtení deníku pro agenta.
- `POST /attachments` a související upload auth doplnit o API key `attachments:write`.

### Frontend

- API typy nesou `version`, `created_by`, `updated_by`, `api_key_id`, externí reference.
- Mutace posílají `If-Match` podle načtené verze.
- React Query refetch:
  - `refetchInterval: 30_000` na relevantních listech/detailu
  - `refetchOnWindowFocus: true`
- Nově přibylé položky vizuálně odlišit, zejména `created_by=agent` a/nebo itemy novější než poslední lokální snapshot.
- Konflikt `409` zobrazit lidsky: „Mezitím upravil agent/uživatel, obnov a rozhodni.“

### Dokumentace pro agenta

- Doplnit OpenAPI popisy endpointů, polí, enumů, examples a jednotné strojové chyby.
- Vygenerovat `AGENT.md` do rootu:
  - dostupné akce
  - curl ukázky
  - API key auth
  - idempotence
  - `If-Match`/version konflikty
  - pravidla pro kalendářovou smyčku: ignorovat `UID` prefix `personalos-` a `X-PERSONALOS-TASK-ID`

### Volitelně MCP server

Pokud to nebude velký zásah: `app/mcp/` za konfiguračním přepínačem, vystavit stejné operace jako tools interně přes service vrstvu, ne HTTP samo na sebe.

### Kroky

1. **Krok 0 — Plán a baseline**
   - Zapsat Fázi 7 do `PLAN.md`/`PROGRESS.md`.
   - Ověřit čistý `main` po Fázi 6B.
   - Commit `faze-7/krok-0: plan agent bridge`.

2. **Krok 1 — ApiKey model, hashování, dependency a CLI přes TDD**
   - RED/GREEN testy: create key zobrazí plaintext jednou, DB ukládá hash+prefix, auth přes `X-API-Key`, revoked/expired odmítnuté, scopes enforced, `last_used_at`, oddělený rate limit config.
   - Commit `faze-7/krok-1: api klice pro agenta`.

3. **Krok 2 — Version/audit původu a konflikt helper přes TDD**
   - Migrace `version`, `created_by`, `updated_by`, `api_key_id` na tasks/notes/challenges/check_ins/attachments podle MVP.
   - RED/GREEN helpery: `If-Match` required for agent writes, mismatch 409 s current, fresh user edit guard.
   - Commit `faze-7/krok-2: optimistic lock a audit puvodu`.

4. **Krok 3 — Tasks/Notes services a UI posílají version**
   - Upravit PATCH/DELETE tasků a notes pro `If-Match`, inkrementace verze, audit původu.
   - Frontend typy/client/hooky posílají `If-Match`, konflikty zobrazují přehledně, polling 30 s + focus refetch, agent-created zvýraznění.
   - Commit `faze-7/krok-3: soubezne upravy tasku a poznamek`.

5. **Krok 4 — Agent context/capture/idempotence přes TDD**
   - `IdempotencyKey` model a service.
   - `GET /agent/context` s ETag.
   - `POST /agent/capture` pro task/note/idea/receipt s inbox fallbackem, externí refs a DB unique pojistkou.
   - Commit `faze-7/krok-4: agent context capture idempotence`.

6. **Krok 5 — Agent complete/checkin/digest/schedule přes TDD**
   - `POST /agent/complete`, `POST /agent/checkin`, `GET /agent/digest`, `GET /agent/schedule`, `PATCH /agent/tasks/{id}/schedule`.
   - Nehádat při více shodách; vracet kandidáty.
   - Commit `faze-7/krok-5: agent operace a schedule`.

7. **Krok 6 — Calendar loop guard a AGENT.md**
   - Upravit `.ics` UID/property.
   - Doplnit `AGENT.md` s curl examples a pravidly ignorování vlastních eventů.
   - Commit `faze-7/krok-6: agent dokumentace a calendar loop guard`.

8. **Krok 7 — API key upload + OpenAPI examples**
   - `POST /attachments` a nutné attachment endpointy podporují API key auth se scope `attachments:write`.
   - Popisy/errors/examples v OpenAPI.
   - Commit `faze-7/krok-7: openapi a attachment auth pro agenta`.

9. **Krok 8 — Full gates, produkční E2E smoke a push**
   - Backend full gates, frontend lint/typecheck/build.
   - Produkční smoke: API key create přes CLI, agent context/capture/duplicate idempotency, UI polling/focus, If-Match conflict, calendar ICS UID/property.
   - Commit a push.

## Fáze 6B — Poznámky, deník a média index

Cíl: navázat na univerzální subsystém příloh a přidat první osobní knowledge/diary vrstvu. Notes/diary mají být jednoduché na každodenní zápis, propojené s úkoly, kategoriemi, vizemi a přílohami. Zároveň se připraví media index pro budoucí automatické párování fotek/videí s deníkovými záznamy a cíli.

### Datový model

`Note`:

- `id`, `owner_id`
- `title`
- `body` — Markdown text
- `kind` — `note`, `diary`, `meeting`, `idea`
- `entry_date` — lokální datum pro deník, volitelné pro obecné poznámky
- `entry_time` — volitelný lokální čas
- `mood` — volitelné krátké označení/nálada
- `category_id` — volitelná vazba na kategorii
- `vision_id` — volitelná vazba na vizi/cíl
- `task_id` — volitelná vazba na úkol
- `created_at`, `updated_at`, `deleted_at`

`NoteAttachment`:

- doplnit FK `note_id -> notes.id ON DELETE CASCADE`
- ponechat `attachment_id`, `position` a unikátní pár `(note_id, attachment_id)`

Volitelný `MediaIndex` pozdější slice:

- `attachment_id`, `captured_at`, GPS, `source`, `indexed_at`, automatické vazby na den podle `captured_at`.

### API

- `GET /notes` — seznam s filtry `kind`, `entry_date`, rozsah dat, `q`, `category_id`, `vision_id`, `task_id`, paging.
- `POST /notes` — create.
- `GET /notes/{id}` — detail.
- `PATCH /notes/{id}` — update.
- `DELETE /notes/{id}` — soft delete.
- `GET /notes/{id}/attachments` — načtení příloh poznámky.
- `POST /notes/{id}/attachments` — napojení existující attachment na poznámku.
- `DELETE /notes/{id}/attachments/{attachment_id}` — odpojení vazby.
- Později: `POST /notes/{id}/attachments/upload` může reuse frontend uploaderu přes obecné hooky.

Bezpečnost:

- Vše chráněné přihlášením a ownership kontrolou.
- Cizí poznámka/vazba/příloha vrací 404.
- Text zůstává Markdown/plain text, frontend ho nesmí renderovat jako nebezpečné HTML.

### Frontend

- Nová navigace „Deník“ / `/notes`.
- Rychlý denní zápis: dnešní diary karta nahoře, vytvořit/upravit bez složitého modálu.
- Seznam poznámek s filtrem druhů a hledáním.
- Detail/editor: title, Markdown textarea, kind, datum/čas, mood, category/vision/task vazby.
- Reuse attachment uploader/grid pro notes přes entity-agnostický wrapper.
- Future-ready media section: zobrazit EXIF datum/GPS, připravit UI pro „přiřadit k dnešnímu deníku“.

### Kroky

1. **Krok 0 — Plán a baseline**
   - Zapsat Fázi 6B do `PLAN.md`/`PROGRESS.md`.
   - Ověřit čistý `main` po Fázi 6A.
   - Commit `faze-6b/krok-0: plan deniku a poznamek`.

2. **Krok 1 — Backend datový model přes TDD**
   - RED testy migrace/modelu: `notes`, `note_attachments` FK, enum `NoteKind`, soft-delete sloupce a vazby na category/vision/task.
   - Modely, migrace, schema skeleton.
   - Fresh Alembic upgrade.
   - Commit `faze-6b/krok-1: datovy model poznamek`.

3. **Krok 2 — Notes CRUD přes TDD**
   - RED/GREEN testy create/list/get/patch/delete, ownership 404, filtry `kind`, `entry_date`, `q`, vazby.
   - Services/routy/schémata.
   - Commit `faze-6b/krok-2: crud poznamek`.

4. **Krok 3 — Přílohy poznámek přes TDD**
   - RED/GREEN testy list/link/unlink note attachments, reuse existující attachments ownership a order `position`.
   - Doplnit service helpery obecně pro `NoteAttachment`.
   - Commit `faze-6b/krok-3: prilohy poznamek`.

5. **Krok 4 — Frontend API/hooky pro notes**
   - TS typy, client metody, TanStack query hooks, invalidace.
   - Commit `faze-6b/krok-4: frontend api poznamek`.

6. **Krok 5 — Frontend Deník/Notes UI**
   - Route `/notes`, navigace, quick diary card, list, detail/editor.
   - Reuse attachment components pro note detail.
   - Commit `faze-6b/krok-5: frontend denik a poznamky`.

7. **Krok 6 — Smoke/gates a push**
   - Backend full gates, frontend lint/typecheck/build.
   - Produkční E2E smoke: login, vytvořit dnešní diary note, přidat text, upload obrázku, ověřit attachment grid, odpojit/smazat, ověřit persistenci po navigaci.
   - Aktualizovat `PROGRESS.md`, commit a push.

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
