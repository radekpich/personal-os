# Personal OS agent contract

## Agent API mutations

When an autonomous agent changes application data through an API key, every mutating request must include an explicit human-readable reason:

- `X-API-Key`: active Personal OS API key.
- `X-Agent-Reasoning`: required, concise explanation of why this mutation is being made.
- `X-Agent-Source`: optional channel/source such as `telegram`, `calendar`, `gmail`, or `manual`.
- `X-Agent-Source-System`: optional upstream subsystem such as `telegram_voice`, `google_calendar`, `garmin`, or `drive_import`.
- `X-Agent-Batch-Id`: optional stable ID shared by all actions derived from one user request/import so the UI can revert them together.

Keep `X-Agent-Reasoning` ASCII-safe for now because HTTP client libraries may reject non-ASCII header values. If a Czech/free-form explanation is needed later, add a JSON request envelope field instead of putting non-ASCII text in the header.

The app automatically records API-key mutations into `agent_actions` with payload/before/result snapshots. Do not manually bypass this audit path for task/note/check-in/file/schedule mutations.

## Agent observability reporting

The `/agent/*` observability endpoints let Personal OS display what Hermes can access, what it watches, what it scheduled, and what it did outside the task audit trail. The app does **not** start or manage Hermes; Hermes reports its own state. Never send plaintext tokens, passwords, OAuth refresh tokens, cookie values, private key material, or full secret environment variables.

### Authentication

Reporting endpoints require an API key with the `agent:report` scope:

```bash
API_KEY='pos_...'
API_URL='http://127.0.0.1:8000'
```

Use `X-API-Key` only. Do not place API keys in URLs, logs, screenshots, or `snapshot_hash` inputs.

### Heartbeat

Send after process start and periodically while alive:

```bash
curl -sS -X POST "$API_URL/agent/heartbeat" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {
      "name": "hermes-default",
      "version": "2026.09.08",
      "host": "vps-main",
      "status": "running",
      "last_error": null
    }
  }'
```

### Registry sync

Send a complete snapshot after startup and after every configuration/access/job/watch/channel change. `snapshot_hash` is the idempotency key for the whole snapshot; compute it from normalized non-secret configuration only.

```bash
curl -sS -X POST "$API_URL/agent/registry/sync" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "agent": {"name": "hermes-default", "version": "2026.09.08", "host": "vps-main", "status": "running"},
  "snapshot_hash": "sha256-normalized-config-without-secrets",
  "jobs": [
    {"name": "Daily briefing", "description": "Morning summary", "schedule": "0 7 * * *", "schedule_description": "daily 07:00", "is_enabled": true, "last_status": "success", "consecutive_failures": 0, "run_count": 12, "tags": ["briefing"]}
  ],
  "integrations": [
    {"name": "Telegram Home", "kind": "telegram", "scopes": ["send_message"], "status": "active", "notes": "Home channel only"}
  ],
  "watches": [
    {"name": "Disk", "description": "VPS disk usage", "kind": "threshold", "config_json": {"metric": "disk_percent", "threshold": 85}, "schedule": "*/30 * * * *", "is_active": true}
  ],
  "channels": [
    {"channel_type": "telegram", "identifier": "Home", "is_active": true, "message_count_24h": 3, "message_count_month": 42}
  ],
  "capabilities": [
    {"name": "google-workspace", "description": "Gmail/Calendar/Drive tools", "is_enabled": true, "metadata_json": {"account": "radek.pich@kexo.cz"}}
  ]
}
JSON
```

A repeated identical `snapshot_hash` returns `idempotent=true` and `changes_created=0`; it must not create new config-change rows. A new/removed/modified job, integration, watch, channel, or capability creates `AgentConfigChange` records visible in the UI until acknowledged.

### Run reporting

Use this for agent activity that is not a direct audited data mutation: scheduled checks, summaries, monitors, imports, or manual operator runs. Single and batch payloads share the same endpoint:

```bash
curl -sS -X POST "$API_URL/agent/runs" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {"name": "hermes-default", "host": "vps-main", "status": "running"},
    "runs": [
      {"trigger": "schedule", "job_name": "Daily briefing", "summary": "Sent morning briefing", "status": "success", "started_at": "2026-09-08T07:00:00Z", "duration_ms": 1840, "tokens_used": 1200, "cost_estimate": 0.02, "tags": ["briefing"]}
    ]
  }'
```

### Watch result reporting

Report watch outcomes by watch UUID from the registry list:

```bash
curl -sS -X POST "$API_URL/agent/watches/$WATCH_ID/report" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "ok", "result": "disk 51%", "triggered": false}'
```

If the watch crosses its threshold, set `triggered=true`; the UI will update `last_triggered_at` and `trigger_count`.

### Security rules

- Report names, kinds, scopes, status, timestamps, and counts — not credentials.
- For integrations, use scoped labels like `gmail.readonly` or `calendar.write`; never include token strings.
- For channels, store human-safe identifiers such as `Home`, `telegram topic`, or redacted chat labels, not secret invite links.
- Treat `/agent/keys/revoke-all` as an emergency human action only from the web UI; agents should not call it.
## Kalendář

Tahle část je aktivní zápis vybraných úkolů do skutečných Google Kalendářů. Nenahrazuje pasivní `.ics` feed aplikace. Aplikace nemá OAuth ani Google tokeny; pouze zadává požadavky do fronty. Zápis provádí agent s vlastním přístupem ke Google Workspace/Calendar.

### Synchronizace seznamu kalendářů

Po startu agenta a potom aspoň jednou denně nahlaš kompletní seznam kalendářů, které může uživatel použít z karty úkolu:

```bash
curl -sS -X POST "$API_URL/agent/calendars/sync" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "calendars": [
    {
      "external_id": "primary-google-calendar-id",
      "name": "Radek",
      "color": "#4285F4",
      "can_write": true,
      "is_shared": false,
      "is_primary": true,
      "is_enabled": true,
      "is_default": true
    },
    {
      "external_id": "katapick-google-calendar-id",
      "name": "KataPick",
      "color": "#0F9D58",
      "can_write": true,
      "is_shared": true,
      "is_primary": false,
      "is_enabled": true,
      "is_default": false
    }
  ]
}
JSON
```

Požadovaný scope API klíče: `calendar:report`. Payload nahrazuje předchozí seznam. Kalendáře bez práva zápisu nastav `can_write=false`; aplikace je nebude nabízet u úkolů, protože zápis by jinak tiše selhal. `is_enabled` je uživatelská nabídka „nabízet u úkolů“ a při dalším syncu ji neposílej jako `true` pro kalendář bez zápisu.

### Zpracování fronty zápisů

Požadovaný scope API klíče: `calendar:write`. Backend po vytvoření/retry/update/delete `CalendarRequest` spouští okamžitý trigger přes `CALENDAR_WRITER_TRIGGER_COMMAND`; primární cesta tedy není polling job. Trigger má provést stejný worker, který umí jednorázově zpracovat aktuální pending frontu. Cron/polling používej jen jako pojistku při výpadku triggeru.

Jednorázový worker:

```bash
curl -sS "$API_URL/agent/calendar-requests?status=pending" \
  -H "X-API-Key: ***"
```

Pro každý požadavek:

1. Zavolej `POST /agent/calendar-requests/{id}/claim`.
2. Pokud dostaneš `409`, požadavek přeskoč — vyzvedla ho jiná instance agenta. Claim je povinný krok; bez něj událost nevytvářej, aby nevznikly duplicity.
3. Proveď operaci v Google Calendaru:
   - `create` vytvoří novou událost,
   - `update` upraví existující událost podle `external_event_id`,
   - `delete` smaže existující událost podle `external_event_id`.
4. Do popisu události vždy vlož odkaz zpět na úkol v Personal OS. Pokud už je v `description` text `Personal OS task: ...`, zachovej ho / převeď na plný odkaz podle nasazení.
5. Používej časovou zónu `Europe/Prague`.
6. Výsledek nahlaš přes `POST /agent/calendar-requests/{id}/complete`:

```bash
curl -sS -X POST "$API_URL/agent/calendar-requests/$REQUEST_ID/complete" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "external_event_id": "google-event-id",
    "external_event_link": "https://calendar.google.com/calendar/event?eid=...",
    "error_message": null
  }'
```

Při chybě pošli `error_message`; aplikace zobrazí stav `failed` a uživatel může požadavek ručně zopakovat.

### Vztah k .ics feedu a čtení kalendáře

Aplikace zapisuje do skutečného kalendáře jen to, co uživatel výslovně zadá z úkolu. Agent může Google Kalendář také číst a navrhovat akce, ale události s UID začínajícím `personalos-` ignoruj — pocházejí z pasivního `.ics` feedu aplikace a nesmí se zpětně importovat ani duplikovat.
