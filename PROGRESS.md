# PROGRESS.md — Personal OS

## Aktuální fáze — Fáze 8B: Hermes registry a provozní přehled

## Hotovo

- [x] 2026-09-11 21:25 UTC — Mobilní regrese 5–11 — safe-area, Markdown, opakování a dokončení úkolů
  - Spodní navigace má globálně větší `workspace` safe-area rezervu a regresní smoke pro všechny hlavní stránky (`/dashboard`, `/tasks`, `/inbox`, `/challenges`, `/diary`, `/visions`, `/agent`, `/settings`) ověřuje doscrollování až na konec bez překrytí posledního obsahu.
  - Přidán bezpečný `MarkdownPreview` přes `react-markdown` bez raw HTML; HTML/script/style se před renderem odstraní. Markdown se renderuje v popisu úkolů, vizí a v těle deníkových poznámek; vývojářská poznámka z formuláře vize odstraněna.
  - `RecurrenceBuilder` má oddělený draft stav, panel vlastního nastavení zůstává otevřený při klikání, nahoře ukazuje průběžné české shrnutí a dole má `Potvrdit`/`Zrušit`; zrušení vrací původní hodnotu.
  - Úkoly ukládají `completed_by` (`user`/`agent`) a `completed_at` nastavuje server v UTC při přechodu do `done`; návrat z hotovo nuluje obě pole. Klientem poslaný `completed_at` se pro dokončení ignoruje, aby statistiky seděly i u API agenta.
  - Detail hotového úkolu zobrazuje `Splněno …`; doplněny backend testy pro user/agent dokončení a ignorování klientského času.
  - Drobnosti: label `Čas (volitelně)`, nový úkol z plného dialogu na stránce Úkoly začíná jako `K udělání`, rychlý zápis zůstává Inbox, hlavička Inboxu je kompaktní řádek s počtem a nápovědou pod ikonou otazníku.
  - Preview DB `/home/zeus/personal-os-preview/phase8b-preview.sqlite` migrována na Alembic head včetně `g5b6c7d8e9f0_add_task_completed_by.py`; preview restartováno (`backend :8030`, `frontend :3030`).
  - Ověření backend: `ruff check app tests`; `pytest -q` → 124 passed. Ověření frontend: `npm run lint`; `npm run typecheck`; `NEXT_PUBLIC_API_BASE_URL=http://38.79.154.155:8030 npm run build` → OK.
  - Smoke: `npm run phase8b:inbox-dashboard-smoke` → `{ ok: true, errors: [] }`; `npm run phase8b:mobile-regression-smoke` → `{ ok: true, errors: [] }`, všechny stránky měly cca 64 px rezervu nad spodní navigací.

- [x] 2026-09-11 05:45 UTC — Mobilní opravy / dávka 4 ze 4 — Inbox jako schránka a akční dashboard
  - Backend úkolů dostal pole `source` a `source_detail` v modelu/schématech/API včetně Alembic migrace `f4a5b6c7d8e9_add_task_source_fields.py`; validní zdroje zahrnují web, rychlý zápis, hlas, Telegram, e-mail, WhatsApp, API, agenta, kalendář a import.
  - Definice Inboxu je nově procesní: úkol patří do Inboxu, když má `status=inbox` nebo mu chybí kategorie/Kde; běžné task view mimo Inbox skrývají nezpracované položky bez kategorie.
  - `/inbox` je samostatná kanálová schránka seskupená podle zdroje s počty, detailem původu, rychlým přiřazením Kategorie/Kde a tlačítkem `Zpracovat`; navigace už nevede na `/tasks?view=inbox`.
  - Dashboard byl zjednodušen na akční dnešek: kompaktní metriky Dnes/Zítra/Po termínu/Inbox, proužek overdue, seznam Dnes a Zítra, dnešní návyky a poslední deníkový zápis; nezpracované inbox položky se na dashboardu nepletou mezi úkoly.
  - Opravena TanStack Query cache pro rychlé dokončení úkolu a následné inline změny, aby dokončený úkol z aktuálního seznamu zmizel a po PATCHi se aktualizovala `version` v cache.
  - Opraven hydration mismatch času v app shellu: čas se renderuje až po mountu klienta.
  - Přidán regresní Playwright smoke `frontend/scripts/phase8b-inbox-dashboard-smoke.mjs` a npm script `phase8b:inbox-dashboard-smoke`; proti preview `http://38.79.154.155:3030` výstup `{ ok: true, errors: [] }`, screenshoty `/tmp/personal-os-8b-dashboard-smoke.png` a `/tmp/personal-os-8b-inbox-smoke.png`.
  - Preview DB `/home/zeus/personal-os-preview/phase8b-preview.sqlite` migrována na head; preview běží na backend `:8030` a frontend `:3030` s buildem proti `NEXT_PUBLIC_API_BASE_URL=http://38.79.154.155:8030`.
  - Ověření backend: `ruff check app tests`; `pytest -q` → 124 passed. Ověření frontend: `npm run lint`; `npm run typecheck`; `NEXT_PUBLIC_API_BASE_URL=http://38.79.154.155:8030 npm run build` → OK.

- [x] 2026-09-10 11:57 UTC — Mobilní opravy / dávka 3 ze 4 — opakování a rozvrh výzev
  - Přidána sdílená frontend komponenta `RecurrenceBuilder`, použitá v detailu úkolu i ve formuláři nové výzvy. Uživatel už nevidí ani nepíše RRULE; komponenta interně parsuje/generuje RRULE přes knihovnu `rrule`.
  - Detail úkolu odstranil textové pole `RRULE opakování`; opakování má rychlé předvolby Denně / Každý pracovní den / Týdně / 3× týdně / Měsíčně, čitelné shrnutí a vlastní nastavení frekvence, intervalu, dnů, měsíční varianty a konce.
  - `Typ opakování` se zobrazuje jen při zapnutém opakování a hodnoty jsou lidsky: `Podle rozvrhu` a `Po dokončení`, včetně vysvětlení typických případů.
  - Výzvy dostaly backend pole `schedule_rrule` v Alembic migraci `e3f4a5b6c7d8_add_challenge_schedule_rrule.py`, validaci přes `python-dateutil` a frontend rozvrh přes stejný `RecurrenceBuilder`; výchozí rozvrh je denně.
  - Přepočet aktuální i nejdelší šňůry respektuje jen plánované dny podle rozvrhu; např. po/st/pá výzva se nepřeruší úterým mimo rozvrh. `Povolené vynechání` počítá vynechané dny z rozvrhu, ne kalendářní dny.
  - `Grace dny` přejmenováno na `Povolené vynechání` s nápovědou „Kolik dní z rozvrhu smím vynechat, aniž se šňůra přeruší.“
  - Heatmapa začíná od startu výzvy, ne od 1. ledna; má popisky Po/St/Pá vlevo, zkratky měsíců nahoře, tooltip datum/hodnota/poznámka/stav a jiný styl pro dny mimo rozvrh; mobilní varianta zůstává vodorovně scrollovatelná se sticky osou.
  - Preview DB `/home/zeus/personal-os-preview/phase8b-preview.sqlite` migrována na head a preview restartováno (`backend :8030`, `frontend :3030`).
  - Ověření backend: `ruff check app tests`; `ruff format --check app tests`; `mypy --strict app tests`; `pytest -q` → 122 passed.
  - Ověření frontend: `npm run lint`; `npm run typecheck`; `NEXT_PUBLIC_API_BASE_URL=http://38.79.154.155:8030 npm run build` → OK.
  - Smoke: `npm run phase8b:recurrence-smoke` proti preview → `{ ok: true, errors: [] }`; původní `npm run phase8b:ui-smoke` také → `{ ok: true, errors: [] }`.

- [x] 2026-09-10 06:02 UTC — Fáze 8B / UI číselníky a sjednocené dialogy
  - Přidána Alembic migrace `d2e3f4a5b6c7_taxonomy_admin_fields.py` pro správu číselníků: barva, ikona, pořadí, archivace a `task_count` ve schématech.
  - Doplněn idempotentní CLI příkaz `python -m app.cli seed-defaults`, který normalizuje default kategorie `KEXO/Ranč/Stavba/Hospodářství/Rodina/Kondice` a místa `Ranč/Staré Buky/Kancelář/Počítač/Telefon/Město/Doma` i ve stávající DB.
  - UI přejmenovalo kontexty na `Kde`/`Místa`; úkoly mají filtr `Všechna místa` a nápovědu „Místo nebo nástroj, kde úkol zvládnu — Ranč, Počítač, Město.“
  - Nastavení má správu Kategorie/Místa/Tagy: seznam, počty úkolů, přidání/editace názvu/barvy/ikony, pořadí drag-and-drop, archivace/smazání; kategorie podporují jednu úroveň rodiče.
  - Přepínač vzhledu byl přesunut do Nastavení a umí `Podle systému` / `Světlý` / `Tmavý`.
  - Quick capture full button i editace používají jeden Task dialog se všemi poli včetně odhadu, tagů, opakování a příloh; desktop side panel a mobile bottom sheet mají sticky akce.
  - Deník používá sjednocený dialog pro nový/editovaný zápis se sticky akcemi; Nová výzva je dialog místo inline formuláře.
  - Preview DB `/home/zeus/personal-os-preview/phase8b-preview.sqlite` migrována na head a seednuta přes `DATABASE_URL=sqlite+aiosqlite:////home/zeus/personal-os-preview/phase8b-preview.sqlite python -m app.cli seed-defaults` → defaulty doplněny/normalizovány.
  - Přidán regresní Playwright smoke `frontend/scripts/phase8b-ui-smoke.mjs` a npm script `phase8b:ui-smoke`; proti preview `http://38.79.154.155:3030` výstup `{ ok: true, errors: [] }`, screenshoty `/tmp/personal-os-8b-ui-desktop-*.png` a `/tmp/personal-os-8b-ui-mobile-*.png`.
  - Ověření backend: `ruff check app tests`; `ruff format --check app tests`; `mypy --strict app tests`; `pytest -q` → 118 passed.
  - Ověření frontend: `npm run lint`; `npm run typecheck`; `NEXT_PUBLIC_API_BASE_URL=http://38.79.154.155:8030 npm run build` → OK.

- [x] 2026-09-09 13:42 UTC — Mobilní opravy / dávka 1 ze 4
  - Opraven bottom-nav safe-area padding a mobilní doscrollování; spodní menu má 4 položky + `Více` panel.
  - Detail úkolu má funkční tag editor: existující tagy, nový tag a odebíratelné odznaky.
  - Deník má opravený nový zápis, chybové hlášky ukládání, přesnější empty text a vlastní rychlou poznámku místo rychlého úkolu.
  - Dashboard filtry vedou na sdílitelné `/tasks?view=...`; Task workspace zachovává URL filtr při změnách a zavírání detailu.
  - Výzvy vrací `active_days_30/90`; UI krátkého běhu ukazuje `běží N dnů` a používá české skloňování.
  - Zmenšena mobilní typografie/odsazení task karet a quick capture dostal submit + plný pohled; zkratková nápověda je jen desktop.
  - Ověření: backend full gate `ruff`/`mypy`/`pytest -q` → 118 passed; frontend `lint`/`typecheck`/production `build` OK; Playwright mobile smoke 375×800 proti preview → OK (`/tmp/personal-os-batch1-mobile.png`).

- [x] 2026-09-08 06:17 UTC — Fáze 8B / Krok 7 — Full-stack gates, production smoke a dokončení
  - Backend registry hotovo: modely/migrace `c1d2e3f4a5b6_add_agent_registry_observability_tables.py`, reporting endpointy `/agent/registry/sync`, `/agent/runs`, read API `/agent/overview`, `/agent/jobs`, `/agent/integrations`, `/agent/watches`, `/agent/channels`, `/agent/config-changes`, `/agent/keys`, emergency `/agent/keys/revoke-all`.
  - Frontend `/agent` rozšířen na záložky Aktivita / Přehled / Úlohy / Přístupy / Hlídání / Historie / Změny / Klíče; původní 8A activity timeline zůstává zachovaná jako samostatná záložka.
  - `AGENT.md` doplněn o reporting kontrakt pro Hermes agenta včetně curl ukázek, rozsahu `agent:report`, snapshot idempotence a pravidla „neukládat plaintext tokeny do registry“.
  - Backend full gate: `ruff check app tests`; `ruff format --check app tests`; `mypy --strict app tests`; `pytest -q` → 118 passed.
  - Frontend full gate: `npm run lint`; `npm run typecheck`; `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8028 npm run build` → production build OK.
  - Produkční E2E smoke: čerstvá SQLite DB, Alembic `head`, seed user, reálný `phase8b-report` API key, živý FastAPI `:8028` + `next start :3028`, `npm run phase8b:smoke` → `ok: true`, snapshot `phase8b-smoke-1788848063688`, ověřen registry sync/idempotence, run history, UI záložky, confirm změny, revoke-all a následné `401` pro revokovaný report key; screenshoty `/tmp/personal-os-phase8b-desktop.png` a `/tmp/personal-os-phase8b-mobile.png`.

- [x] 2026-09-07 — Fáze 8B / Krok 0 — Plán a baseline
  - Zapsána Fáze 8B do `PLAN.md`: read-only Hermes registry, reporting endpointy, snapshot diff, runs/history, watches, keys emergency revoke-all, frontend záložky a retention cleanup.
  - Ověřen čistý `main`: `git status --short --branch` → `## main...origin/main`.
  - Založen pracovní checklist pro modely, registry sync, run reporting, read API, frontend, AGENT.md a produkční smoke.

- [x] 2026-09-07 16:26 UTC — Fáze 8A / Část A — AgentAction audit, activity timeline a revert
  - Přidán `AgentAction` model, schéma a Alembic migrace `b9e0f1a2c3d4_add_agent_action_audit_log.py` s payload/before/result snapshoty, reasoning, source/source_system, batch_id, latency a reverted_at.
  - API-key mutace přes Tasks/Notes se automaticky logují middlewarem; mutace přes `X-API-Key` vyžadují `X-Agent-Reasoning` a podporují `X-Agent-Batch-Id`.
  - Přidáno `/agent/actions` API: timeline, filtry action/source/source_system/entity/date/only_unreverted, single revert a batch revert s optimistic conflict ochranou.
  - Přidána frontend stránka `/agent`: timeline, filtry, checkbox výběr, bulk revert, diff rozbalení před/po a conflict náhled.
  - Agent badge v seznamech úkolů/poznámek odkazuje do filtrované Agent aktivity pro daný záznam; doplněno `AGENT.md` pravidlo pro reasoning/source/batch hlavičky.
  - Ověření backend: `ruff check app tests`; `ruff format --check app tests`; `mypy --strict app tests`; `pytest -q` → 112 passed; čerstvý Alembic `upgrade head`.
  - Ověření frontend: `npm run lint`; `npm run typecheck`; `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8018 npm run build`.
  - Produkční E2E smoke: čerstvá SQLite DB, reálný API key přes CLI, živý FastAPI + `next start`, `npm run phase8a:smoke` → `ok: true`, task `758be7ed-290e-49cf-876b-ac1ba0666133`, screenshoty `/tmp/personal-os-phase8a-desktop.png` a `/tmp/personal-os-phase8a-mobile.png`.

- [x] 2026-09-07 08:18 UTC — Fáze 7 / Krok 2 — Versioning, audit původu a konflikty
  - Přidána `version`, `created_by`, `updated_by`, `api_key_id` pole do `tasks` i `notes` v modelech, schématech a Alembic migraci.
  - PATCH/DELETE pro Tasks i Notes vyžadují `If-Match`; chybějící hlavička vrací `428 if_match_required`.
  - Version mismatch vrací `409 version_conflict` v jednotném JSON tvaru včetně `current_state` aktuálního záznamu.
  - Přidán service helper `app.services.concurrency` s `MutationActor`, `VersionConflict`, `FreshUserEditConflict`, `ensure_can_mutate`, `apply_mutation_audit`.
  - Agentí změna čerstvě člověkem upraveného záznamu vrací 409 přes configurable `FRESH_USER_EDIT_GUARD_MINUTES`.
  - Aktualizovány backend testy na nový kontrakt a opravena determinističnost jednoho staršího challenge testu.
  - Ověření: `pytest -q` → 106 passed; `ruff check`, `ruff format --check`, `mypy --strict`; čerstvý Alembic `upgrade head`.

- [x] 2026-09-07 07:56 UTC — Fáze 7 / Krok 1 — API klíče pro stroje
  - Přidán `ApiKey` model a Alembic migrace `api_keys`: `owner_id`, `name`, `key_hash`, `key_prefix`, `scopes`, `last_used_at`, `expires_at`, `revoked_at`, `created_at`.
  - Klíč se generuje jako plaintext jen při vytvoření (`pos_...`), do DB jde jen SHA-256 hash a zobrazovací prefix.
  - Přidána samostatná `X-API-Key` FastAPI dependency oddělená od cookie auth: `get_current_api_key`, `require_api_key_scope`.
  - Přidáno ověření revokace, expirace, scopes a aktualizace `last_used_at`.
  - Přidán config `RATE_LIMIT_API_KEY_DEFAULT` jako samostatný limit pro machine klienty.
  - Přidán CLI příkaz `create-api-key` a `revoke-api-key`.
  - TDD ověření: `pytest tests/test_api_keys.py -q` → 4 passed; `ruff check`, `ruff format --check`, `mypy --strict`; Alembic `upgrade head` na čerstvé DB.

- [x] 2026-09-07 07:53 UTC — Fáze 7 / Krok 0 — Plán a baseline
  - Zapsána Fáze 7 do `PLAN.md`: API klíče, oddělená strojová autentizace, scopes, optimistic locking přes `version`/`If-Match`, audit původu, fresh-edit guard, idempotence, agent endpointy, calendar loop guard, AGENT.md a volitelný MCP server.
  - Ověřen čistý `main` po Fázi 6B: `git status --short --branch` → `## main...origin/main`.
  - Založen pracovní checklist pro model API klíčů, concurrency/audit, agent endpointy, frontend polling/conflicts, dokumentaci a smoke.

### Fáze 6B — Poznámky, deník a média index

- [x] 2026-09-07 10:15 UTC — Fáze 6B / Krok 7 — Produkční E2E smoke Deníku
  - Doplněn `frontend/scripts/phase6b-smoke.mjs` a npm script `phase6b:smoke`.
  - Smoke běží přes Playwright proti reálnému loginu a `/diary`: vytvoří dnešní diary note, ověří persistenci po navigaci, nahraje PNG přílohu, ověří attachment grid/lightbox/download URL a odpojí přílohu.
  - Mobile smoke ověřuje `/diary` a viditelnost bottom nav.
  - Reálný smoke výstup: `ok: true`, `diaryTitle=Smoke deník 1788766468504`, screenshoty `/tmp/personal-os-phase6b-desktop.png` a `/tmp/personal-os-phase6b-mobile.png`.
  - Ověřeno: čerstvá SQLite DB + Alembic `head`, seed user, živý FastAPI backend, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:53961 npm run build`, `next start`, `npm run phase6b:smoke`, `npm run lint`, `npm run typecheck`.

- [x] 2026-09-06 19:02 UTC — Fáze 6B / Krok 6 — Full-stack gates a dokončení
  - Backend full gate: `pytest -q` → 98 passed; `ruff check app tests`; `ruff format --check app tests`; `mypy --strict app tests` zelené.
  - Frontend full gate: `npm run lint`; `npm run typecheck`; `npm run build` zelené, `/diary` zahrnuto v produkčním buildu.
  - Fáze 6B dokončila první knowledge/diary vrstvu nad attachment subsystémem.

- [x] 2026-09-06 18:55 UTC — Fáze 6B / Krok 5 — Frontend Deník/Notes UI
  - Přidána navigace `Deník` a route `/diary`.
  - Nový `NoteWorkspace` umí list poznámek, filtr typ/q, vytvoření, editaci, mazání, datum/čas, mood, kategorii a vizi.
  - Attachment komponenty `AttachmentUploader` a `AttachmentGrid` jsou zobecněné pro `taskId` i `noteId`.
  - Detail poznámky podporuje upload/list/lightbox/popisky/odpojení/smazání příloh přes note attachments API.
  - Ověřeno: `npm run lint && npm run typecheck` zelené.

- [x] 2026-09-06 18:46 UTC — Fáze 6B / Krok 4 — Frontend API typy a hooky pro poznámky
  - Doplněny typy `NoteKind`, `Note`, `NoteList`, `NoteFilters`, `NoteCreate`, `NoteUpdate`, `NoteAttachment`.
  - `api` klient umí Notes CRUD a note attachment list/link/unlink.
  - React Query má query keys a hooky `useNotes`, `useNote`, `useCreateNote`, `useUpdateNote`, `useDeleteNote`, `useNoteAttachments`, `useUploadNoteAttachment`, `useDeleteNoteAttachment`, `useUnlinkNoteAttachment`.
  - Ověřeno: `npm run lint && npm run typecheck` zelené.

- [x] 2026-09-06 18:42 UTC — Fáze 6B / Krok 3 — Backend přílohy poznámek
  - Přidány schémata `NoteAttachmentCreate` a `NoteAttachmentRead`.
  - `attachment_service` nově umí `list_note_attachments`, `attach_to_note`, `detach_from_note` nad `NoteAttachment`.
  - Soft-delete attachmentu čistí vazby z `task_attachments` i `note_attachments`.
  - Router `/notes` má endpointy `GET/POST /notes/{note_id}/attachments` a `DELETE /notes/{note_id}/attachments/{attachment_id}`.
  - TDD ověřeno: RED chybějící note attachment endpoint vracel 404; GREEN `pytest tests/test_note_attachments.py -q` → 2 passed.
  - Slice gates: `pytest tests/test_notes_model.py tests/test_notes_api.py tests/test_note_attachments.py tests/test_attachments_endpoints.py -q` → 10 passed; `ruff`; `ruff format --check`; `mypy --strict` zelené.

- [x] 2026-09-06 18:38 UTC — Fáze 6B / Krok 2 — Notes CRUD backend
  - Přidána schémata `NoteCreate`, `NoteUpdate`, `NoteRead`, `NoteList`.
  - Přidán `note_service` s create/list/get/patch/delete, soft-delete a filtry `kind`, `entry_date`, `date_from`, `date_to`, `q`, `category_id`, `vision_id`, `task_id`.
  - Přidán router `/notes` a zapojení do FastAPI.
  - Ownership ochrana: cizí poznámka i cizí vazby category/vision/task vrací 404.
  - TDD ověřeno: RED `/notes` vracelo 404; GREEN `pytest tests/test_notes_api.py -q` → 3 passed.
  - Slice gates: `pytest tests/test_notes_model.py tests/test_notes_api.py -q` → 5 passed; `ruff`; `ruff format --check`; `mypy --strict` zelené.

- [x] 2026-09-06 18:32 UTC — Fáze 6B / Krok 1 — Backend datový model poznámek
  - Přidán model `Note` a enum `NoteKind` (`note`, `diary`, `meeting`, `idea`).
  - `notes` obsahuje Markdown body, diary datum/čas, mood a volitelné vazby na kategorii, vizi a úkol.
  - `note_attachments.note_id` má nově FK na `notes.id ON DELETE CASCADE`.
  - Přidána migrace `e2a7b4c9d1f3_add_notes.py` včetně batch alteru pro existující `note_attachments`.
  - TDD ověřeno: RED padal na chybějící `app.models.note`; GREEN `pytest tests/test_notes_model.py -q` → 2 passed.
  - Slice gates: `ruff`, `ruff format --check`, `mypy --strict` pro nové soubory zelené.

- [x] 2026-09-06 18:24 UTC — Fáze 6B / Krok 0 — Plán a baseline
  - Zapsána Fáze 6B do `PLAN.md`: Notes/diary model, API, frontend Deník, note attachments a budoucí media index.
  - Ověřen čistý `main` po Fázi 6A: `git status --short --branch` → `## main...origin/main`.
  - Založen pracovní checklist pro backend model, CRUD, přílohy poznámek, frontend API/UI a E2E smoke.

- [x] 2026-09-05 16:18 — Fáze 6A / Krok 7 — Full-stack gates a dokončení
  - Spuštěn celý backend gate: `pytest -q` → 91 passed; `ruff check app tests`; `ruff format --check app tests`; `mypy --strict app tests`.
  - Spuštěn frontend gate: `npm run lint`; `npm run typecheck`; `npm run build` → Next.js production build úspěšný.
  - Opraven starší datumově závislý test named views pro neděli v Europe/Prague.
  - Fáze 6A připravena k pushi.

- [x] 2026-09-05 16:03 — Fáze 6A / Krok 6 — Storage usage v Nastavení
  - Settings panel načítá `GET /storage/usage` přes nový hook `useStorageUsage`.
  - Přidán přehled využito/zbývá/počet souborů, progress bar, limit a ruční refresh.
  - Ověřeno: `npm run lint && npm run typecheck`.

- [x] 2026-09-05 15:55 — Fáze 6A / Krok 5 — Frontend uploader/grid/lightbox v task detailu
  - Doplněny frontend typy `Attachment`, `TaskAttachment`, `StorageUsage` a multipart podpora ve fetch clientu.
  - Přidány API metody/hooky pro upload, link/list příloh úkolu, popisky, smazání/odpojení a storage usage.
  - Vytvořeny reusable komponenty `AttachmentUploader` a `AttachmentGrid` s drag & drop/file inputem, náhledy, PDF fallbackem, lightboxem, popiskem, odpojením a smazáním.
  - Detail úkolu nyní obsahuje sekci příloh pod editačním formulářem.
  - Backend doplněn o `GET /tasks/{id}/attachments`, aby frontend mohl načítat vazby úkolu.
  - Ověřeno: frontend `npm run lint && npm run typecheck`; backend attachment slice 11 passed + `ruff` + `mypy --strict`.

- [x] 2026-09-05 15:38 — Fáze 6A / Krok 4 — Endpointy, task vazby a cleanup
  - Doplněny endpointy `GET /attachments/{id}/thumb`, `PATCH /attachments/{id}`, `DELETE /attachments/{id}`.
  - `GET`/thumb jsou chráněné vlastnictvím a po soft-delete vrací 404.
  - `DELETE /attachments/{id}` dělá měkké mazání a smaže vazby z `task_attachments`; fyzické soubory zůstávají do cleanup retention.
  - Doplněny `POST /tasks/{id}/attachments` a `DELETE /tasks/{id}/attachments/{attachment_id}` přes join tabulku `task_attachments` s `position`.
  - Cizí task/attachment se maskuje 404.
  - Přidána cleanup funkce a APScheduler daily job přes FastAPI lifespan; maže fyzické soubory u soft-delete záznamů starších 30 dní a osiřelé soubory bez DB záznamu.
  - TDD ověřeno: attachment endpoint/processing/api testy → 11 passed; slice gates `ruff`, `mypy --strict` zelené.

- [x] 2026-09-05 15:20 — Fáze 6A / Krok 3 — Background processing obrázků/PDF
  - Přidán processing po uploadu přes FastAPI `BackgroundTasks`; response stále vrací `processing_status=pending`, DB záznam po jobu přejde na `ready` nebo `failed`.
  - Obrázky se načítají přes Pillow, aplikuje se EXIF Orientation, delší hrana se zmenší na 2000 px a výsledek se uloží jako JPEG kvalita 85 bez EXIF metadat.
  - Před smazáním EXIF se ukládá `DateTimeOriginal` a GPS do `captured_at`, `gps_lat`, `gps_lon`.
  - HEIC je podporované přes `pillow-heif` a po zpracování se převádí na JPEG.
  - Náhledy se generují jako JPEG s delší hranou max 400 px.
  - PDF se nekomprimuje ani nepřepisuje; přes `pypdfium2` se generuje JPEG náhled první stránky.
  - TDD ověřeno: `pytest tests/test_attachments_api.py tests/test_attachments_processing.py -q` → 8 passed; slice gates `ruff`, `mypy --strict` zelené.

- [x] 2026-09-05 15:05 — Fáze 6A / Krok 2 — Upload příloh a limity
  - Přidány endpointy `POST /attachments`, `GET /attachments/{id}` a `GET /storage/usage`.
  - Upload čte `UploadFile` po chunkech, hlídá `MAX_ATTACHMENT_SIZE_MB`, zapisuje do temp souboru a až potom atomicky `os.replace` na serverem generovanou UUID cestu.
  - Typ souboru se určuje podle magic bytes, ne podle přípony ani `Content-Type`; povoleny JPEG, PNG, WebP, HEIC a PDF.
  - Přidána sanitizace původního názvu proti path traversal; fyzická cesta se nikdy negeneruje z klientského filename.
  - Přidána kontrola `MAX_STORAGE_MB`, storage usage payload a ownership ochrana: cizí attachment vrací 404.
  - Deduplikace přes `(owner_id, checksum_sha256)`: opakovaný stejný upload vrací existující attachment a nevytváří druhý fyzický soubor.
  - TDD ověřeno: `pytest tests/test_attachments_api.py -q` → 6 passed; slice gates `ruff`, `mypy --strict` zelené.

- [x] 2026-09-05 14:45 — Fáze 6A / Krok 1 — Backend datový model a config
  - Přidán model `Attachment` s požadovanými metadaty, `processing_status` a soft-delete `deleted_at`.
  - Přidány spojovací modely/tabulky `task_attachments(task_id, attachment_id, position)` a připravený vzor `note_attachments(note_id, attachment_id, position)` bez polymorfního `entity_type`.
  - Přidána migrace `c8f2a1d9e0b4_add_attachments.py` a storage settings `ATTACHMENTS_DIR`, `MAX_ATTACHMENT_SIZE_MB`, `MAX_STORAGE_MB`.
  - TDD RED potvrzeno: testy padaly na chybějící settings/tabulky/migraci.
  - GREEN ověřeno: `pytest tests/test_attachments_model.py -q` → 3 passed; slice gates `ruff`, `mypy --strict` zelené.

- [x] 2026-09-05 14:24 — Fáze 5 / Krok 7 — E2E smoke a finální ověření
  - Přidán `npm run phase5:smoke` a Playwright smoke script `frontend/scripts/phase5-smoke.mjs`.
  - Smoke běží proti čerstvé SQLite DB, Alembic `head`, reálnému FastAPI backendu a produkčnímu `next start`.
  - Ověřeno E2E: login, založení `daily_action`, one-tap dnešní check-in, ověření rekord/streak, založení `abstinence`, zapsání relapsu, desktop screenshot.
  - Ověřeno mobile visual smoke: stránka `/challenges`, bottom nav a mobilní screenshot; heatmapa má extra spodní scroll rezervu (`pb-20`) proti fixed bottom nav.
  - Smoke výstup: `ok: true`; screenshoty `/tmp/personal-os-phase5-desktop.png`, `/tmp/personal-os-phase5-mobile.png`.
  - Finální backend gate: `ruff check .`, `ruff format --check .`, `mypy --strict app tests`, `pytest -q` → 77 passed.
  - Finální frontend gate: `npm run lint`, `npm run typecheck`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:53921 npm run build` zelené.

- [x] 2026-09-05 14:14 — Fáze 5 / Krok 6 — Frontend stránka Návyky
  - Přidána `/challenges` stránka a navigace „Návyky“ v sidebaru i spodní navigaci.
  - Přidány challenge karty s velkým číslem aktuální šňůry, rekordem, cílem a one-tap akcí: daily check-in / abstinence relaps.
  - Přidán formulář pro založení výzvy s typem, kategorií, vizí, cílem dní, grace days a barvou.
  - Přidána GitHub-style heatmapa: 7 řádků, sloupce po týdnech, tooltip s datem/poznámkou/pauzou, mobile horizontal scroll.
  - Ověřeno frontend gate: `npm run lint`, `npm run typecheck`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:53901 npm run build` zelené.

- [x] 2026-09-05 14:09 — Fáze 5 / Krok 5 — Frontend API typy/hooks
  - Přidány TS typy `Challenge`, `ChallengeCreate/Update`, `CheckIn`, `CheckInResult`, `ChallengeStats`, `ChallengeHeatmap`.
  - Přidány API client metody pro `/challenges`, `/stats`, `/heatmap`, check-in a pause.
  - Přidány TanStack Query hooks a invalidace po check-in/pause/create/update/delete.
  - Ověřeno: `npm run lint`, `npm run typecheck`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:53901 npm run build` zelené.

- [x] 2026-09-05 14:06 — Fáze 5 / Krok 4 — Stats a heatmap endpointy
  - Přidány `GET /challenges/{id}/stats` a `GET /challenges/{id}/heatmap?year=`.
  - Stats vrací `current_streak`, `longest_streak`, `total_count`, `success_rate_30`, `success_rate_90`.
  - Success rate se počítá přes aktivní lokální dny od `started_at`, s pauzami vyjmutými z denominatoru.
  - Heatmapa vrací celý rok po dnech (`365/366`) včetně `value`, `note`, `is_relapse`, `is_paused`, `has_check_in`, `intensity`.
  - Ověřeno full backend gate: `ruff check .`, `ruff format --check .`, `mypy --strict app tests`, `pytest -q` → 77 passed.

- [x] 2026-09-05 14:02 — Fáze 5 / Krok 3 — Abstinence logika
  - Doplněny testy pro odmítnutí úspěšného check-inu u `abstinence`: zapisuje se pouze relaps.
  - Ověřeno, že relaps resetuje aktuální šňůru na 0 a rekord zůstává nejdelší období bez relapsu.
  - Doplněn RED→GREEN test pro pauzu u `abstinence`: pauzované dny se nepočítají do elapsed streaku.
  - `abstinence` výpočet zůstává v samostatné funkci `_calculate_abstinence_streaks`; `daily_action` má oddělenou `_calculate_daily_action_streaks`.
  - Ověřeno: `pytest tests/test_challenges.py -q` → 9 passed; `ruff check`, `ruff format --check`, `mypy --strict app tests/test_challenges.py` zelené.

- [x] 2026-09-05 13:58 — Fáze 5 / Krok 2 — Daily action záludnosti
  - Doplněny testy pro `allowed_gap_days`, backfill limit 7 dní, odmítnutí budoucnosti a timezone lokální den.
  - Doplněn RED→GREEN test pro pauzu: interval pauzy se vyjme z gapu, nepočítá se do šňůry a po návratu pokračuje streak.
  - `daily_action` výpočet teď používá pause-aware aktivní gap, nikoliv hrubý kalendářní rozdíl.
  - Ověřeno: `pytest tests/test_challenges.py -q` → 7 passed; `ruff check`, `ruff format --check`, `mypy --strict app tests/test_challenges.py` zelené.

- [x] 2026-09-05 13:42 — Fáze 5 / Krok 0 — Plán a baseline
  - Zapsána Fáze 5 do `PLAN.md`: Challenges/CheckIns, oddělené logiky `daily_action` vs `abstinence`, timezone pravidla, backfill limit, grace period, pauzy, idempotence, stats a heatmapa.
  - Ověřen čistý repo stav po Fázi 4: `main...origin/main` bez lokálních změn.
  - Založen pracovní checklist pro backend model, výpočty šňůr, stats/heatmap, frontend a E2E smoke.

- [x] 2026-09-05 13:52 — Fáze 5 / Krok 1 — Backend datový základ přes TDD
  - Přidány modely `Challenge`, `CheckIn`, `ChallengePause` a enum `ChallengeType`.
  - Přidána migrace `a5c2f91e6b37_add_challenges_and_check_ins.py`; fresh SQLite Alembic upgrade ověřil tabulky `challenges`, `check_ins`, `challenge_pauses`.
  - Přidány základní `/challenges` endpointy: list/create/get/patch/delete, `POST /challenges/{id}/check-in`, `POST /challenges/{id}/pauses`.
  - Přidána unikátní idempotence `(challenge_id, date)` pro check-in; druhý zápis stejného dne dělá update a vrací 200.
  - Už v datovém základu existují oddělené výpočtové funkce pro `daily_action` a `abstinence`, aby se neslily dvě odlišné logiky.
  - TDD RED ověřeno: `pytest tests/test_challenges.py -q` nejdřív padal na chybějící `/challenges` a `challenge_service`.
  - GREEN ověřeno: `pytest tests/test_challenges.py -q` → 4 passed.
  - Slice gates ověřeny: `ruff check`, `ruff format --check`, `mypy --strict app tests/test_challenges.py`.

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

- [x] 2026-09-05 07:49 — Fáze 4 / Krok 4–7 — Frontend Visions, navázání úkolu a E2E smoke
  - Přidány frontend typy/API metody/hooks pro `Vision`, `VisionTreeNode`, `VisionProgress`, `StagnatingVision` a `Task.vision_id`.
  - Přidána stránka `/visions` se stromovým pohledem, rozbalováním, native drag/drop přes změnu `parent_id`, progress bary a panel stagnujících vizí.
  - Upraven detail úkolu: select `Vize / cíl`, ukládání `vision_id`; seznam úkolů zobrazuje navázanou vizi jako badge.
  - Upraven Dashboard/Task workspace tak, aby načítal vize a invalidoval vision cache po změně úkolu.
  - Přidán `npm run phase4:smoke` (`frontend/scripts/phase4-smoke.mjs`) pro produkční E2E: login, založení vize, drag/drop vnoření, quick task, navázání úkolu na vizi, ověření progressu a mobile visual smoke.
  - Smoke odhalil reálný cache bug (`0/0` progress po navázání úkolu); opraveno invalidací `visions` queries v `useUpdateTask`.
  - Ověřeno backend: `ruff check .`, `ruff format --check .`, `mypy --strict app tests`, `pytest -q` → 66 passed.
  - Ověřeno frontend: `npm run lint`, `npm run typecheck`, `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:53911 npm run build`.
  - Ověřeno E2E: produkční backend + `next start` + `npm run phase4:smoke` → OK; screenshoty `/tmp/personal-os-phase4-desktop.png`, `/tmp/personal-os-phase4-mobile.png`.

## Rozpracováno

- Fáze 7 / Krok 3 — Tasks/Notes UI posílá `version`, používá polling/focus refetch a zobrazuje nové agent položky.

## Další krok

Doplnit frontend API typy a mutace tak, aby PATCH/DELETE posílaly `If-Match`; nastavit TanStack Query `refetchInterval: 30000`, focus refetch a vizuální odlišení položek `created_by=agent`/nově přibylých po pollingu.

## Poznámky

- Od Fáze 2 platí resumable workflow: každý samostatný krok končí aktualizací tohoto souboru a git commitem.
- Projekt je git repozitář v `/home/zeus/personal-os`, remote `git@github.com:radekpich/personal-os.git`.
- Backend je v `backend/`, frontend ve `frontend/`.
- Backend Fáze 2 je dokončený a ověřený 56 testy + live E2E smoke.
- Fáze 3 dodává každodenně použitelný frontend úkolovníku.
- Fáze 4 přidává modul Visions: strom dlouhodobých cílů + klíčové napojení na úkoly přes `Task.vision_id`.
