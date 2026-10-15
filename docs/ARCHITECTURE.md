# Architecture

The brief ([`PROJECT_BRIEF.md`](PROJECT_BRIEF.md)) is the specification. This file records how
the code implements it. Update it when the structure changes.

## Processes

| Process | Command | Notes |
|---|---|---|
| API | `uvicorn app.main:app` (port 8000) | FastAPI; JWT bearer auth |
| Worker | `huey_consumer app.jobs.huey` | Huey with SQLite storage at `data/huey.db` |
| Web | `next dev` / standalone `server.js` (port 3000) | Next.js App Router, talks to the API via `NEXT_PUBLIC_API_URL` |

All persistent state lives in `./data` (gitignored; a Docker volume, an encrypted EBS volume in
production).

## Backend layers

```
api/ (routers) ──► services/* (use-cases) ──► models/ (SQLAlchemy) ──► SQLite / PostgreSQL
                         │
                         └──► services/engine + services/hosting  (pure functions, no DB, no LLM)
```

- **core/** — settings (`pydantic-settings`), DB engine with SQLite pragmas applied in the
  `connect` event (and sqlite-vec loaded there), argon2 + JWT, and `tenancy.py`
  (`scoped()` / `get_owned()`), the only sanctioned way to query tenant tables.
- **api/deps.py** — `CurrentUser`, role guards (`EditorUser`, `AdminUser`), `can_see_margin`.
- **Roles** — `admin`, `estimator`, `finance`, `viewer`. Margin visible to `finance`/`admin` only.
- **Migrations** — Alembic with `render_as_batch=True`; the DB URL comes from app settings.
  Tests run all migrations against a fresh temporary SQLite file.

## Guard rails enforced by tests

- `tests/test_architecture.py` — `services/engine` and `services/hosting` may not import
  `app.llm`, any LLM SDK, SQLAlchemy, models or the API layer.
- `tests/core/test_db.py` — WAL, `busy_timeout`, `foreign_keys`, `synchronous` and sqlite-vec are
  active on every connection.

## Frontend

Next.js 16 App Router under `frontend/src/app`. Hand-written shadcn/ui-style primitives in
`src/components/ui`. API calls go through `src/lib/api/client.ts`; types are generated from the
backend OpenAPI schema with `make openapi` (`src/lib/api/schema.d.ts`). The token is kept in
`localStorage` (`aakalan.token`) for v1.
