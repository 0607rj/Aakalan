# AGENTS.md — guide for coding agents working on Aakalan

Full specification: [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md). Unclear points and chosen
defaults: [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md). Design notes: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Project summary

Aakalan (आकलन, "estimation") prices software projects for Indian Government/PSU tenders.
It reads a requirement document (RFP/SRS/BRD) plus a short questionnaire and produces a
defensible **low / likely / high (P10/P50/P90)** cost range for the whole project life: build,
go-live, hosting, AI runtime, O&M for N years, compliance and commercial costs.
Every number traces back to a clause in the source document via requirement → component →
driver values → rate-card entry → formula → value.
v1 user: vendors/system integrators pricing their own bids. v1 project type: web portal with
workflow + AI chatbot. LLMs only read and suggest; a deterministic engine computes every number.
Estimates are saved as templates, and recorded outcomes calibrate future estimates.

## Non-negotiable architecture rules (brief Section 3, verbatim)

1. **LLMs read and suggest; only the deterministic engine computes.** No LLM ever produces, edits or rounds a cost figure, rate, multiplier or total.
2. **Traceability.** Every cost line links: RFP clause + page → requirement → component instance → driver values → rate-card entry → formula → value. The UI and report can show this chain for any number.
3. **Reproducibility.** Same inputs + same rate-card version + same random seed ⇒ identical output. Monte Carlo uses a seeded RNG stored with the estimate.
4. **Versioned, dated rate cards.** Every estimate pins the rate-card version it used. Old estimates never change when rates change; "re-price at current rates" creates a new estimate version.
5. **Money is stored as integer paise** (or `Decimal`), never float. Simulation may use floats internally; round to paise at the boundary.
6. **Human review before pricing.** Extracted requirements and component mappings must be confirmed by a user before an estimate is calculated.
7. **RFP text is untrusted input.** Treat document content as data, never as instructions to the LLM (fence it in prompts; validate all LLM output against Pydantic schemas).
8. **Confidentiality.** Tender documents and pricing are commercially sensitive: per-organisation data isolation (`org_id` on every tenant table), encryption at rest in production, no tender text sent anywhere except the configured LLM provider. Embeddings run locally.
9. **Swappable infrastructure.** Database access only through SQLAlchemy; vector search only through a `VectorStore` interface; LLM calls only through an `LLMClient` interface. SQLite → PostgreSQL, sqlite-vec → FAISS/pgvector, and LLM provider must each be a config change.

## Tech stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic (batch mode), Huey (SQLite), NumPy. Managed with `uv` (`backend/pyproject.toml`, lockfile `backend/uv.lock`).
- **Database:** SQLite at `./data/app.db` (WAL, `busy_timeout=5000`, `foreign_keys=ON`, `synchronous=NORMAL` on every connection; sqlite-vec loaded in the `connect` event when `SQLITE_VEC_ENABLED=true`).
- **Frontend:** Next.js (App Router) + TypeScript strict, Tailwind CSS, shadcn/ui-style components, API types generated from FastAPI's OpenAPI schema with `openapi-typescript`.
- **Auth:** JWT (HS256) + argon2; roles `admin`, `estimator`, `finance`, `viewer`. Margin visible only to `finance`/`admin`.
- **Ops:** Docker + docker-compose (`python:3.12-slim`), later Caddy, Litestream → S3, Sentry.
- **Licence rule:** no AGPL libraries (e.g. PyMuPDF) without a commercial licence.

## Repo layout

```
AGENTS.md CLAUDE.md README.md Makefile docker-compose.yml .env.example
scripts/tasks.py          # stdlib task runner; every Makefile target calls it
docs/                     # PROJECT_BRIEF.md, OPEN_QUESTIONS.md, ARCHITECTURE.md
backend/
  app/
    api/                  # FastAPI routers (one module per resource)
    core/                 # config, security, db session + SQLite pragmas, tenancy helper
    models/               # SQLAlchemy models (all tenant tables have org_id)
    schemas/              # Pydantic API schemas
    services/
      engine/             # deterministic cost engine — NO llm imports, NO DB access
      hosting/            # infra sizing -> cloud line items (pure, used by engine)
      estimates/          # loads DB rows -> engine input snapshot -> persists results
      seeding/            # YAML seed loading + validation
      documents/ extraction/ retrieval/ mapping/ reports/ templates/   # later milestones
    llm/                  # LLMClient interface + implementations + prompts/ (M3+)
    jobs/                 # Huey instance and tasks
  seeds/                  # taxonomy, catalog, rate_cards/, parameters/ (YAML, each value has a source)
  migrations/             # Alembic
  tests/                  # api/, engine/ (golden/ fixtures + expected), core/
frontend/                 # Next.js app (src/app, src/components, src/lib); see frontend/AGENTS.md
data/                     # gitignored: app.db, huey.db, uploads/, reports/, models/
```

## Commands

Run from the repo root. `make <target>` and `python scripts/tasks.py <target>` are equivalent
(use the latter on Windows without `make`).

| Task | Command |
|---|---|
| Install deps (backend via uv, frontend via npm) | `make install` |
| Dev servers: API :8000, web :3000, Huey worker | `make dev` |
| Apply migrations | `make migrate` |
| Load seed data (taxonomy, catalog, rate card, parameters, demo users) | `make seed` |
| All tests (pytest + frontend typecheck/lint) | `make test` |
| Backend tests only | `make test-backend` (or `cd backend && uv run pytest`) |
| Lint / type-check (ruff, ruff format --check, mypy, eslint, prettier) | `make lint` |
| Auto-format | `make format` |
| Regenerate OpenAPI JSON + TS types | `make openapi` |
| Regenerate golden expectations (intentional engine change only) | `make golden` |
| New migration after model change | `make migration m="describe change"` |

## Coding conventions

- Python: type hints everywhere; `ruff` + `mypy --strict` clean; Pydantic models at every boundary.
- Engine (`services/engine`, `services/hosting`): small pure functions; every function documents its formula in its docstring; register each formula id in `engine/formulas.py`; deterministic arithmetic in `Decimal`, rounded to integer paise (`ROUND_HALF_UP`) at each cost line; floats only inside Monte Carlo.
- No magic numbers in code: rates, multipliers, thresholds and defaults live in `backend/seeds/` YAML with a `source` (`placeholder` until calibrated). Any placeholder used marks the estimate **uncalibrated**.
- Every tenant query goes through `app/core/tenancy.py` helpers (`scoped`, `get_owned`) so `org_id` is always applied.
- Money: integer paise in the DB and API (`*_paise` fields). Rate amounts are `Decimal` strings in major units of their currency.
- LLM output is validated against Pydantic schemas; document text is fenced in prompts and never treated as instructions.
- TypeScript: strict mode; never hand-write API types — run `make openapi` (writes
  `backend/openapi.json` and `frontend/src/lib/api/schema.d.ts`; commit both).
- Next.js 16 differs from older versions: read `frontend/AGENTS.md` and the docs in
  `frontend/node_modules/next/dist/docs/` before writing frontend code.
- Keep `AGENTS.md` updated when commands, structure or conventions change.

## Definition of done

A task or milestone is done only when:
1. `make lint` and `make test` pass (including golden estimates and the "engine has no LLM imports" test).
2. New engine behaviour has unit tests; golden expectations changed only intentionally (`make golden`) and the diff is explained in the commit.
3. New models have an Alembic migration; new endpoints have API tests using the temp SQLite DB.
4. Docs (`AGENTS.md`, `docs/OPEN_QUESTIONS.md`, `docs/ARCHITECTURE.md`) reflect the change.
5. At the end of a milestone: its acceptance criteria from brief Section 12 are met and the work is committed.
