# PLAN.md — Personal OS

## Fáze 2 — Jádro aplikace: kategorie, kontexty, štítky, úkoly, opakování a iCalendar

Cíl: rozšířit existující backend po Fázi 1 o chráněné owner-scoped doménové jádro aplikace. Každý krok musí skončit funkčním stavem, aktualizovaným `PROGRESS.md` a git commitem ve formátu `faze-2/krok-N: ...`.

### Krok 0 — Baseline a pracovní pravidla

Soubory:
- `PLAN.md`
- `PROGRESS.md`
- existující backend soubory z Fáze 1

Úkoly:
- založit git repozitář, pokud neexistuje;
- zapsat plán Fáze 2;
- zapsat počáteční progress;
- commitnout baseline před prvním produkčním kódem Fáze 2.

### Krok 1 — Uživatelský profil pro calendar token

Soubory:
- `backend/app/models/user.py`
- `backend/app/schemas/user.py`
- `backend/alembic/versions/*_add_calendar_token_to_users.py`
- `backend/tests/test_calendar_token.py`

Úkoly:
- přidat `calendar_token` do `User` jako unikátní neveřejný bearer token pro ICS feed;
- doplnit migraci;
- otestovat, že token existuje a lze jej regenerovat pozdějším endpointem.

### Krok 2 — Category a Context CRUD

Soubory:
- `backend/app/models/category.py`
- `backend/app/models/context.py`
- `backend/app/schemas/category.py`
- `backend/app/schemas/context.py`
- `backend/app/services/category_service.py`
- `backend/app/services/context_service.py`
- `backend/app/api/routes/categories.py`
- `backend/app/api/routes/contexts.py`
- `backend/app/api/routes/__init__.py`
- `backend/app/main.py`
- `backend/alembic/versions/*_add_categories_contexts.py`
- `backend/tests/test_categories.py`
- `backend/tests/test_contexts.py`

Úkoly:
- přidat owner-scoped modely Category a Context;
- Category: `name`, `color`, `icon`, `parent_id`, `position`, `is_archived`, `owner_id`, timestamps, `deleted_at`;
- Context: `name`, `position`, `is_archived`, `owner_id`, timestamps, `deleted_at`;
- validovat hex color;
- zajistit dvouúrovňové vnoření kategorií;
- endpointy musí používat `get_current_user` a filtrovat podle `owner_id`.

### Krok 3 — Tag a M:N vazba na Task základ

Soubory:
- `backend/app/models/tag.py`
- `backend/app/models/task.py`
- `backend/app/schemas/tag.py`
- `backend/app/schemas/task.py`
- `backend/app/services/tag_service.py`
- `backend/app/api/routes/tags.py`
- `backend/alembic/versions/*_add_tags_tasks.py`
- `backend/tests/test_tags.py`

Úkoly:
- přidat Tag s owner scopingem;
- připravit M:N tabulku task_tags;
- přidat minimální Task model potřebný pro vazbu;
- CRUD tagů a owner izolace.

### Krok 4 — Task CRUD, quick inbox a komplexní filtrování

Soubory:
- `backend/app/models/task.py`
- `backend/app/schemas/task.py`
- `backend/app/repositories/task_repository.py`
- `backend/app/services/task_service.py`
- `backend/app/api/routes/tasks.py`
- `backend/tests/test_tasks.py`

Úkoly:
- Task fields: `title`, `description`, `status`, `priority`, `due_date`, `due_time`, `estimate_minutes`, `completed_at`, `category_id`, `context_id`, `parent_task_id`, `position`, `tags`, owner/timestamps/deleted_at;
- enumy status/priority;
- `POST /tasks/quick` přijímá jen holý text a vytváří inbox task;
- `GET /tasks` filtry: status, category, context, tags, due date range, fulltext, pagination;
- named views: `today`, `this_week`, `overdue`, `inbox`;
- všechny dotazy owner-scoped.

### Krok 5 — Opakované úkoly

Soubory:
- `backend/app/models/task.py`
- `backend/app/schemas/task.py`
- `backend/app/services/task_service.py`
- `backend/tests/test_recurrence.py`

Úkoly:
- přidat `recurrence_rule` jako RRULE string a `recurrence_mode` (`fixed`, `after_completion`);
- při dokončení opakované instance generovat další instanci, ne předem tisíce řádků;
- fixed počítat podle RRULE, after_completion od dokončení;
- otestovat oba režimy.

### Krok 6 — Calendar ICS feed

Soubory:
- `backend/app/services/calendar_ics_service.py`
- `backend/app/api/routes/calendar.py`
- `backend/tests/test_calendar_ics.py`
- případně `backend/app/core/config.py` a `.env.example` pro veřejný calendar hostname, pokud bude potřeba

Úkoly:
- `GET /calendar/{token}.ics` bez přihlášení, read-only podle `User.calendar_token`;
- `POST /calendar/regenerate-token` chráněné přihlášením;
- VEVENT, ne VTODO;
- all-day `DTSTART;VALUE=DATE` pro task bez času;
- timed event s délkou `estimate_minutes` nebo 30 minut;
- vložit `VTIMEZONE` pro Europe/Prague;
- stabilní UID podle task ID;
- RRULE exportovat jako jednu událost;
- správné hlavičky `Content-Type: text/calendar; charset=utf-8` a `Cache-Control`.

### Krok 7 — Seed data migrace

Soubory:
- `backend/alembic/versions/*_seed_phase2_data.py`
- `backend/tests/test_seed_data.py`

Úkoly:
- seed kategorie: KEXO, Ranč na Valech, Stavba, Hospodářství, Rodina, Kondice;
- seed kontexty: @ranč, @Staré Buky, @počítač, @telefon, @město;
- seed ukázkové úkoly včetně `Zkontrolovat zdivo a rozvody` a opakovaného krmení zvířat;
- seed provést bezpečně pro existujícího nebo demo uživatele bez rozbití single-user auth.

### Krok 8 — Finální audit, dokumentace a smoke

Soubory:
- `backend/README.md`
- `backend/.env.example`
- `PROGRESS.md`

Úkoly:
- aktualizovat dokumentaci endpointů;
- spustit `ruff check`, `ruff format --check`, `mypy --strict`, `pytest -q`;
- ověřit čerstvou SQLite DB přes `alembic upgrade head`;
- vytvořit uživatele přes CLI;
- smoke: login, quick task, list inbox, CRUD category/context/tag, calendar token regenerate, ICS feed;
- commitnout finální stav.
