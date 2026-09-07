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
