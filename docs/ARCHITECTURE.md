# Architecture

The brief ([`PROJECT_BRIEF.md`](PROJECT_BRIEF.md)) is the specification. This file records how
the code implements it. Update it when the structure changes.

## Processes

| Process | Command | Notes |
|---|---|---|
| API | `uvicorn app.main:app` (port 8000) | FastAPI; JWT bearer auth |
| Worker | `huey_consumer app.jobs.huey` | Huey with SQLite storage at `data/huey.db` |
| Web | `next dev` / standalone `server.js` (port 3000) | Next.js App Router, talks to the API via `NEXT_PUBLIC_API_URL` |

All persistent state lives in `./data` (gitignored; an encrypted EBS volume in production).
Production runs without Docker: systemd services behind Caddy (`docs/DEPLOY.md`).

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
2. `components.base_effort` — effort per component (brief 7.1); from parameters v20 an
   `EffortPlan` worked out once from all components (project reuse ratio, effort caps) scales
   review, tests, pre-build and architect work → `timeline.build_timeline`:
   natural duration from a monotone max-team curve, size band, compression / extension, or
   *not feasible* with a phased plan. `core.schedule` works out the timeline and the fastest
   deadline that still gets a price without pricing anything; the quick estimate prices a
   deadline below it at that fastest time and says so (OPEN_QUESTIONS 179).
3. Base lines: component labour (× compression), go-live, hosting (`services/hosting`),
   AI runtime, maintenance, programme, EMD and exit.
4. Derived commercial lines from `commercial.derived_amounts` (contingency, working capital,
   PBG, penalty reserve, margin, GST).
5. `simulation.simulate` — triangular Monte Carlo, one seeded quantile stream per uncertainty
   group, derived lines recomputed per run with the same function; P10/P50/P90 and bucket
   variance shares (top range drivers; lines marked `follows_build`, such as project
   management, are left out because their spread is the build's).

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

**Three sizes for one build** (OPEN_QUESTIONS 163). Beside our feature-by-feature price, the
summary shows the independent check (`anchor.py`, a build counted from the document's items)
and the story-size check (`size_check.py`): each feature's user stories sized with Simple
Function Points at the ISBSG delivery rate, compared with our hours without AI tools, with the
features furthest from their story size listed. Both are checks only: they never change a
price, and the range is not narrowed when they agree (no coverage evidence yet).

**Fewer, broader lines** (parameters v25 + rate card v10, OPEN_QUESTIONS 166). Hosting is one
line a year (`hosting.bundle.v1`): a monthly rate for the whole set-up by provider, plan and
load band, with the load inside the band as the line's own spread; without a v10 rate card it
stays itemised (`hosting/sizing.py`). Upkeep (bug fixes, patches, upgrades, small changes) is
one line a year (`maintenance.upkeep.v1`). Work the engine prices is not priced again when a
staff line already does it: onsite developers / L2-L3 do the upkeep and an onsite project
manager is the O&M project manager (`OnsiteResource.covers`, set in `quick/service.py` from
the role's name); the annual re-audit starts in support year 2; year 1 leaves out the
hypercare weeks.

**The price follows what is built, not who orders it** (quick config v2, parameter set v12).
There is no client-type question. Each ticked feature has a level (`feature_levels`: basic /
standard / advanced, `sizing.levels`) that sets its components' size and complexity and adds
points; the total points pick a `sizing.tiers` entry: the project size (`project_size`
driver, for the size factor, lean delivery and model error), the standard building blocks and
their size, and default training / hypercare. Client-specific work is an explicit, priced
answer: security audit (`cert_in_audit` + VAPT fixes), formal reports and meetings
(`governance_overheads`), accessibility and languages (features). "Where will it run?" picks
the hosting provider and whether the server bill is in the cost (`existing` = client's own
servers, listed separately). "How much will the team use AI tools?" sets `team_ai_maturity`
(default: the company's saved AI level).

The summary carries, besides the plain parts and cost items, `feature_costs` (each feature's
component lines, shared components split evenly, the rest as "standard building blocks") and,
on every cost item and feature, `traditional_paise`: the same line priced without AI tools
(`result.traditional.lines`, stored with the estimate). Parameter set v12 adds the line
`build.testing/ai_code_review` (`build.ai_code_review.v1`): `review_share_of_saved` × the
person-days AI tools save × the review role's rate, so the AI saving is net of checking the
AI's work.

Source eras (catalog v6): every component records its effort `evidence` and a `source_era`
(`pre_ai` / `ai_assisted` / `unknown`, derived from the evidence; a date before
`era_rules.pre_ai_before_year` is only a provisional `date_heuristic`).
`components.ai_saving_applies` decides whether the team's AI savings reduce a component: always
for catalogs without eras (v1-v5, as before), once for `pre_ai`, never for `ai_assisted`, and
for `unknown` only when `EstimateInput.era_scenario == "pre_ai_sensitivity"`. The review line
is priced on the saving actually applied, so it follows automatically. Lines of v6 components
use `component_labour.v3` and record `source_era`, `evidence`, `ai_saving` and `era_scenario`.
`estimates.service.era_sensitivity` runs the engine a second time with unknown-era components
read as pre-AI (same seed and reference data, like `traditional_price`) and stores
`result.era_sensitivity`: that run's P10/P50/P90 and the range `min(P10 of both) .. P90 of the
estimate`. The estimate's P50 stays the price; the quick summary shows the second run beside it
(`era_sensitivity`). `calibration_basis` in catalog v6 documents what `effort_multiplier` was
checked against (not reproducible; never changes a source era). Catalog-level notes
(`era_rules`, `calibration_basis`) live in the seed file; the database mirror stores components.

Scope items (`QuickRequest.scope`, quick config `scope`): `plan_quick` turns each chosen item
into a `scope` requirement and adds its catalog blocks at their levels after the features'
blocks, through the same `component_reqs` / `component_level` merge (one block per key, the
larger level wins; a standard block is sized `max(tier.base_size, item size)`). Blocks only
items asked for carry the item's label and get their own `feature_costs` row. The engine is
unchanged: the added blocks are priced, era-checked and simulated like any other component.
Both readers return `scope` findings with a status (prompt `extract_tender_v5`; the basic reader's
`_scope` reads each matched sentence: ruled out / later phase / asked for / only mentioned).
`verify_findings` keeps known keys with a quote found on the page: `explicit` and `inferred`
are offered (`scope`), `excluded`, `future` and `background` are listed apart
(`scope_set_aside`); a corrigendum can rule an item out when files are merged;
`ScopeStep` (both flows) marks them *Suggested* and never ticks them for the user: only ticked items are sent and priced. Chosen items are planned in the config's order, so the order they were ticked never changes component ids or the simulation's draws. An item may ask for a standard block only at basic (config validator): a whole size step is a larger module, not one item's increment. The summary's `scope_items` gives each chosen item's added building cost (0 = its block was already there).

Risk and market comparison (parameter set v16): no fixed contingency; the Monte Carlo is the one
risk mechanism and `risk_allowance = P50 − planned`. The engine's `market_check.v1` (P50 ×
`market_by_size`) only runs for parameter sets that still have bands (v14-v15). The summary's
market box (`quick.service._published_prices`) is computed from `seeds/benchmarks/<country>.yaml`
instead: benchmarks the app gives the same size (`_benchmark_sizes`, via
`calibration.backtest.derived_size`, cached per country), neighbouring sizes added below
`market_comparison.min_projects`, prices in today's money with GST, P25 / median / P75, sources
by web address. It is descriptive, never scaled to the estimate and never fed back into it.
`calibration.backtest.backtest(..., as_of=)` adds `segments` (`segment_metrics`: median |error|,
bias = exp(median log ratio), P10-P90 coverage and band hits by size, app size and client
type) to its report.

The manual and document flows ask one thing per screen (`estimate/new/steps.tsx`, `?step=<key>`
in the web address): features → first version or full product (optional "change levels") →
(document: key numbers) → each `group: main` question → deadline → the optional `detail`
questions on one screen → check your answers → calculate. Options can add features
(`add_features`: mobile app, other software, old data — `hidden` features, not tick boxes), set
the default level (`feature_level`), change a standard block's complexity
(`component_complexity`, e.g. a ready design) or be "Not sure" (`unsure`: the usual answer, with
requirement clarity lowered per `not_sure`, so the range widens). A "Not sure" with `left_out`
(old data, other software) instead leaves its features out of the price; `priced_options` quotes
them "if required" and, with `plan_quick(include_left_out=True)`, at the usual size (the
earlier behaviour). The summary also lists the team by role (`team`, `support_team`) from the
engine's manpower rows.

What a quote rests on and leaves out (OPEN_QUESTIONS 147) is listed on the result page, the PDF
and the Excel from the same summary fields: `assumed` (questions that matter, answered neither
on the form — `QuickRequest.answered` — nor by the document) and `not_included` (features and
scope items marked "Not included", standard blocks unticked on the form, items "Not sure" left
out, the document's exclusions and not-priced topics). The form gets the size's standard
blocks from `POST /quick-estimate/standard-blocks`; a description's "no mobile app" is found by
`extraction/describe.py:ruled_out` (code, keyword windows from the quick config).

The features screen (OPEN_QUESTIONS 150), the same for a description and an uploaded document
(`frontend/src/app/estimate/new/feature-sections.tsx`), is laid out in the frontend only, with no new pricing:
found in the description, included by default (the standard blocks), a fixed shortlist
(`QuickOptions.commonly_needed`, from the quick config) minus what was found, then browse all
(closed). The kind of software orders the shortlist and ticks nothing. A feature a question
adds (mobile app, other software, old data) is ticked by setting that question's answer.

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

## Countries, company settings and calibration

Reference data is per country (`region` on rate cards and parameter sets; currency on the rate
card). `services/settings.py` applies the company's margin / buffer / effort multipliers to a
copy of the parameter set before pricing. The headline back-test is the **production path** (`backtest_production`, OPEN_QUESTIONS 161): each benchmark with a saved reading (`tests/fixtures/readings_v9`, the readings plus staff lines entered by hand, OPEN_QUESTIONS 162) is priced as an upload is, through the review form's pre-fill (`services/quick/prefill.review_prefill`, which the form itself loads from `GET /documents/{id}/form`) and `plan_quick` with the reading passed in. Staff during support come from the reading's staff lines (prompt v9): `services/extraction/staffing.py` applies the rules in code (price table wins, call-off as written, staffed shifts only for a committed team, months from the line, helpdesk only when asked for, chatbot complex only with the buyer's systems) and raises the pre-bid queries; the request's `staff` list becomes the engine's `onsite_resources` (`maintenance.onsite.v2` / `support_staff.v2` for months or round-the-clock seats), and the form shows these key answers first within their topic (support, build), ordered by price impact (`key_answers`); the form asks one topic at a time (quick config `topics`, OPEN_QUESTIONS 177). The rest of this paragraph describes the **legacy path, not the production path**: `services/calibration/backtest.py` prices the
benchmark contracts in `seeds/benchmarks/<country>.yaml` with the same quick-estimate mapping
(features at the level matching each project's size class, the size pinned to that class,
government projects above small with the audit and formal reporting asked for). From
parameter set v12, `--calibrate` (`fit_pooled`) fits one build-effort factor per project size
(`size_effort_multiplier`) on custom builds of **every client type together**, then the
ready-made-product factor (`answer_effort_multiplier`), and reports leave-one-out errors (each
project priced with a factor fitted without it) as the honest accuracy; client types are only
reported, never priced. The model error is by project size (`model_spread_by_size`). Older
sets (v6–v11) also had buyer-segment factors (`segment_effort_multiplier`,
`segment_size_effort_multiplier`), still honoured by the engine for old estimates. Published prices are brought to today's money with the
parameter set's labour escalation; a published price band counts as exact when our price is
inside it. Accepted results become a new parameter-set version.

For private and small-business buyers (v12: for small projects, whoever the client is),
parameter sets v6 / us-v5 onwards also apply **lean delivery**
(`lean` group: build PM, hypercare and O&M PM capped as a share of build effort; a test
environment priced as one small cloud server) and a **shared model error**
(`calibration.model_spread`): `simulation.py` multiplies every base line in a run by one
triangular draw, because estimation error is systematic and does not average out across
building blocks. Government estimates are unchanged by both.

## Third-party costs and client-paid items

`services/engine/third_party.py` (parameter sets with a `third_party` group: v5, us-v4):

- `dev_tools_lines` — build-phase seats (AI coding assistant, dev tools suite) per person-month of
  build effort, bucket `build.tools`.
- `third_party_lines` — usage-billed services from `third_party.services` (bases `monthly`,
  `per_user`, `fixed`; conditions on components, buyer segment, country, users and cloud hosting),
  plus `ai_feature_lines` for AI features other than the chatbot. Cloud-side services follow
  `hosting_in_scope`; the rest follow `usage_fees_in_scope`.
- `translation_lines` — one-off translation per extra language and yearly updates.
- `client_paid_lines` / `client_paid_notes` — what the client pays providers directly: hosting
  they provide (priced on a copy of the context with hosting in scope), usage fees they take on,
  and per-transaction rates such as payment gateway fees. These go to
  `EstimateResult.client_paid` / `client_paid_notes`, fully traced but **excluded from totals**;
  the quick summary groups them as `client_pays`.

Taxonomy is versioned like the catalog (`seeds/taxonomy/v1.yaml`, `v2.yaml`); estimates use the
newest, golden tests stay on v1.

## Frontend

Next.js 16 App Router under `frontend/src/app`. Hand-written shadcn/ui-style primitives in
`src/components/ui`. API calls go through `src/lib/api/client.ts`; types are generated from the
backend OpenAPI schema with `make openapi` (`src/lib/api/schema.d.ts`). The token is kept in
`localStorage` (`aakalan.token`) for v1.

The public pages and sign-in screens share `src/components/site`: `EmberHero` (the top panel with
the white mist), `DotScene` (each page's dot picture, a mask from `public/hero`), `SiteNavBar` (floating pills that gather on scroll) and the cards in
`sections.tsx`. Colours and fonts are tokens in `globals.css`, so the logged-in app follows them.
