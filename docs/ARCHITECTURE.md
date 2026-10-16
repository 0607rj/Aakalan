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

## Estimation engine (M1)

`services/engine` + `services/hosting` are pure Python: no database, no LLM, no I/O.

```
EstimateInput (snapshot)                                   EstimateResult
  requirements (clause+page, clarity)                        lines[] with full trace
  components (catalog key, size, complexity, qty, req ids)   totals: base case, P10/P50/P90
  answers (questionnaire, cite req ids)        calculate()   by stage / bucket / year
  taxonomy · catalog · rate card · parameters ──────────────► timeline, manpower
  as_of_date · seed                                          top range drivers, confidence
                                                             calibration (placeholders used)
```

Pipeline inside `core.calculate`:

1. `context.resolve_questionnaire` — answers over parameter-set defaults; defaults become assumptions.
2. `components.base_effort` — effort per component (brief 7.1) → `timeline.build_timeline`:
   natural duration from a monotone max-team curve, size band, compression / extension, or
   *not feasible* with a phased plan.
3. Base lines: component labour (× compression), go-live, hosting (`services/hosting`),
   AI runtime, maintenance, programme, EMD and exit.
4. Derived commercial lines from `commercial.derived_amounts` (contingency, working capital,
   PBG, penalty reserve, margin, GST).
5. `simulation.simulate` — triangular Monte Carlo, one seeded quantile stream per uncertainty
   group, derived lines recomputed per run with the same function; P10/P50/P90 and bucket
   variance shares (top range drivers).

Every line is built through a `LineBuilder` that records each driver (with the requirements
the answer cites), rate item (with rate-card version and source), parameter (with
parameter-set version and source), formula id (`formulas.py`) and intermediate step. That
record *is* the trace returned by `GET /estimates/{id}/lines/{line_id}/trace`.

Determinism: Decimal arithmetic in a fixed context, `ROUND_HALF_UP` to integer paise per
line, explicit `as_of_date` (never "today" inside the engine), NumPy PCG64 seeded per group.
Golden fixtures in `tests/engine/golden/*.yaml` with expectations in `*.expected.json`
(`make golden` to regenerate intentionally).

Reference data is versioned and immutable: seed YAML → `taxonomy_versions`,
`catalog_components`, `rate_cards`/`rate_items`, `parameter_sets`. An estimate stores its
whole `EstimateInput` snapshot, so it can always be reproduced; "re-price" builds a new
version from the same snapshot with the current reference versions.

## Estimate flow (API)

```
POST /projects → POST /projects/{id}/requirements (manual, confirmed)
              → PUT  /projects/{id}/questionnaire
              → PUT  /projects/{id}/components   (saving = confirmation)
              → POST /projects/{id}/estimates     (409 unless everything is reviewed)
              → GET  /estimates/{id} · GET /estimates/{id}/lines/{line_id}/trace
              → POST /estimates/{id}/scenarios · POST /estimates/{id}/reprice
```

`services/estimates/service.py` turns rows into the snapshot and persists results
(`estimates`, `cost_lines` with trace JSON, `assumptions`). Margin lines, margin inputs and the
`margin_percent` answer are redacted for `estimator` and `viewer`.

## Quick estimate (simple mode)

`api/quick.py` + `services/quick/`: `POST /quick-estimates` takes a project name, ticked
feature keys and plain answers, creates a confirmed project (features → requirements,
components from `seeds/quick_estimate.yaml`, answers → questionnaire), runs the normal estimate
and returns a `QuickSummary` (headline range, five plain parts, build-only cost, build months,
biggest uncertainty in words). `GET /estimates/{id}/summary` rebuilds the summary for any
estimate. The summary only regroups integer paise produced by the engine.

## Document reading (M3, scoped to simple mode)

```
POST /documents ─► services/documents/parsing.py   PDF (pdfplumber) / DOCX → page texts
                ─► services/extraction/tender.py   ai_read (LLMClient, prompt llm/prompts/extract_tender_v1.md)
                │                                   or basic_read (keywords) when no key is set
                └► verify_findings                  drop anything whose quote is not on its page
POST /quick-estimates {document_id, features, choices, overrides}
                ─► requirements cite document + clause + page → engine → trace back to the page
```

`app/llm/client.py` defines the `LLMClient` protocol (`AnthropicClient`, `FakeClient` for
tests); the provider and model are configuration. The engine never imports it (tested).

## Reports and outcomes

`services/reports/data.py` reads the stored estimate once and feeds both `pdf.py` (reportlab)
and `excel.py` (openpyxl), so exports show exactly the API's numbers:
`GET /estimates/{id}/report.pdf`, `GET /estimates/{id}/boq.xlsx`. `services/outcomes.py` records
bid results (`POST /projects/{id}/outcome`) and builds the calibration report (`GET /calibration`).

## Frontend

Next.js 16 App Router under `frontend/src/app`. Hand-written shadcn/ui-style primitives in
`src/components/ui`. API calls go through `src/lib/api/client.ts`; types are generated from the
backend OpenAPI schema with `make openapi` (`src/lib/api/schema.d.ts`). The token is kept in
`localStorage` (`aakalan.token`) for v1.
