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
  Look (OPEN_QUESTIONS 189): orange accent and Stack Sans Headline, Google Sans Flex, IBM Plex Mono
  everywhere; public pages open on the ember panel (`components/site/ember-hero.tsx`), each with its
  own dot picture (`dot-scene.tsx`, `public/hero`, drawn by code, not by an image AI), always light
  below it, with `.soft-card` and `.dark-card`; the logged-in app is laid out as a web app: an ink
  sidebar with the ember glow (`components/app-sidebar.tsx`; a top bar and drawer on phones), each
  page's title on a faint warm grid with no box (`components/app-hero.tsx`, `.app-head`; the
  new-estimate steps too, `.step-head`) and soft white cards below in one column. Each thing is said on one page only (OPEN_QUESTIONS 189).
- **Auth:** JWT (HS256) + argon2; roles `admin`, `estimator`, `finance`, `viewer`. Margin is shown to every role, and margin,
  safety buffer and the AI saving are one rule for everyone, never a company's choice; company
  settings keep only facts about the team: day rates, AI-tool use (OPEN_QUESTIONS 227).
  Sign-up creates a company with the person as admin; email verified and password reset by emailed
  6-digit codes (`services/auth.py`, hashed, expiring, limited tries); a reset or change raises the
  user's `token_version` (`tv` in the JWT) so older tokens stop working. Wrong passwords
  slow sign-in down per email and per address (`login_failures`, settings `login_*`,
  429 with Retry-After; OPEN_QUESTIONS 188). Verifying an email needs the code and the
  sign-up's password; company names are not unique. Sign-ups and contact messages per
  address an hour, and AI calls per company a day, are limited (`services/limits.py`, table
  `rate_events`, settings `*_max_per_*`, 0 = off; OPEN_QUESTIONS 190). Rate cards are
  published by the owner only. Bid results and the
  calibration report are owner-only (`OWNER_EMAILS`, `OwnerUser`, `is_owner` on `/auth/me`).
  The owner's Admin page (`/admin`, `api/owner.py`, OPEN_QUESTIONS 172) is the one place that reads
  across organisations: every account and its estimates, the shared features waiting for approval
  (OPEN_QUESTIONS 190), disable, role, verify, delete, and "view as"
  (a read-only token naming the owner, `act`; `viewed_by_owner` on `/auth/me`); a disabled
  account signing in with the right password gets 423 "turned off", and the person is emailed
  on disable, enable and delete (OPEN_QUESTIONS 222). Email through
  `services/email.py` (SMTP, or the server log in development; tests use `set_email_sender`);
  every email's text and HTML copy come from `services/email_templates.py` (OPEN_QUESTIONS 223).
- **Ops:** no Docker. One Ubuntu server: systemd services (API, Huey worker, Next.js standalone)
  behind Caddy (`deploy/`, [`docs/DEPLOY.md`](docs/DEPLOY.md)); later Litestream → S3, Sentry.
- **Licence rule:** no AGPL libraries (e.g. PyMuPDF) without a commercial licence.

## Repo layout

```
AGENTS.md CLAUDE.md README.md Makefile .env.example
deploy/                   # Ubuntu server: systemd units, Caddyfile, update.sh (docs/DEPLOY.md)
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
                          #   core.calculate(EstimateInput) -> EstimateResult; formulas.py registry;
                          #   context.LineBuilder records the trace of every line
      hosting/            # infra sizing -> cloud line items (pure, used by engine)
      estimates/          # DB rows -> EstimateInput snapshot -> engine -> persisted Estimate
      seeding/            # seed YAML loading, DB seeding, demo data, golden fixtures
      quick/              # simple mode: plain features/questions -> project -> estimate -> summary
                          #   prefill.py: the review form's pre-fill from a reading (GET
                          #   /documents/{id}/form), also what the production-path back-test prices
                          #   reality.py: "does this price look real?" checks (explain only);
                          #   second_opinion.py: AI review of scope and levels (words, no numbers)
                          #   anchor.py: independent check, a build counted from the document's
                          #   items; far from the price => export blocked until confirmed
                          #   (POST /estimates/{id}/check/confirm); open answers priced as
                          #   options (GET /estimates/{id}/options)
                          #   size_check.py: the build sized from the document's user stories
                          #   (Simple Function Points × ISBSG hours per FP, config `size_check`)
                          #   beside our hours without AI tools, per feature; a check only, no
                          #   verdict on a CMS / ready-product build (OPEN_QUESTIONS 163)
                          #   stories.py: no document => the AI drafts user stories per feature
                          #   (POST /quick-estimate/draft-stories) on the results page ("What
                          #   each feature includes", GET/PUT /estimates/{id}/stories), the user
                          #   checks and saves them (`feature_stories`; the typed `description`
                          #   is saved for it); size check only, never price or seed
                          #   sources.py: where every price comes from, read from each line's
                          #   trace (GET /estimates/{id}/sources; results page, PDF page, Excel
                          #   "Sources" sheet); words in config `price_sources` (ai_studies,
                          #   margin: the published margins the profit was checked against);
                          #   each source published / worked out / our estimate (OPEN_QUESTIONS 226)
                          #   context.py: shown only, never priced (OPEN_QUESTIONS 205): the
                          #   industry (reading prompt v10 `project_domain`), the project type
                          #   (most features shared with a `project_types` entry) and user roles
                          #   (from the stories); prerequisite warnings (config
                          #   `project_context.prerequisites`, and add-ons whose feature is not
                          #   ticked) that never add anything; five-domain reading measurement
                          #   outside the tests: backend/measurements/domains/
                          #   quote lists (OPEN_QUESTIONS 147): answers nobody gave
                          #   (`assumed`, the form sends `answered`), `not_included`
                          #   (features / scope / unticked standard blocks, the document's
                          #   exclusions); "Not sure" with `left_out` (old data, other
                          #   software) leaves the item out, quoted "if required"
      research/           # a feature the catalog lacks: catalog match, else AI web search with the
                          #   code checking every page, else AI analysis as catalog blocks; saved
                          #   per org (ResearchedComponent, auto-approved) and reused; config
                          #   `research:` in quick_estimate.yaml; nothing searched without a key;
                          #   the form lists the company's own by section ("Researched before");
                          #   library.py offers every block to all companies (no tenant data),
                          #   live only once the owner approves it, under an anonymous key:
                          #   table shared_researched_components + seeds/research/library.yaml;
                          #   a shared block prices a matching typed feature but is never listed
                          #   or named to another company (`catalog_for(shared=False)` for lists,
                          #   results show the user's own words; OPEN_QUESTIONS 185);
                          #   deploy/update.sh keeps the server's own entries (cli library-merge)
      documents/          # upload storage + PDF/DOCX parsing to page texts
      extraction/         # tender reading: AI (LLMClient) or basic keyword reader + citation check,
                          #   describe.py: "Find features" from a typed description; the AI's
                          #   reading is kept per org by the text's sha256 (table
                          #   description_readings), so the same words give the same features
                          #   merge of several files (corrigenda override), pre-bid queries;
                          #   the upload step takes up to `project_max_documents` (5) files with a
                          #   type each; the same file once; the check counts all (OPEN_QUESTIONS 225)
                          #   inventory.py: AI lists quoted items for the independent check
                          #   (tried `inventory_tries` times; an AI-read document left uncounted
                          #   needs a person's confirm before export, OPEN_QUESTIONS 186)
                          #   client_provided.py: "hosting / domain / SSL provided by the
                          #   department" (or by the client's own name) answers those questions
                          #   (code, cited); support_terms.py: support hours and stated support
                          #   staff, with a pre-bid query on a contradiction (OPEN_QUESTIONS 157)
                          #   coverage.py: requirement sentences ("shall", "must") no finding
                          #   quotes, listed on the review screen as not priced yet (config
                          #   `coverage`, OPEN_QUESTIONS 204); after an AI reading the features
                          #   are only the AI's: no keyword or count adds one (217)
                          #   a contract-terms page lists nothing (`terms_page`, 219)
                          #   uptime_terms.py: the uptime an SLA table asks for ("<99.5%")
                          #   answers the downtime question, cited (config `uptime_terms`, 219);
                          #   an answer quoting only the tendering process (config
                          #   `tender_process`) or a "not stated" sentence is dropped (218, 219)
                          #   a feature found only on pages of terms is offered unticked
                          #   (`outside_scope`); our own report uploaded is flagged (`own_report`, 220)
                          #   stated_counts.py: "200 services" / "integration with 20 State
                          #   Systems" make that feature several modules, cited (config
                          #   `stated_counts`, OPEN_QUESTIONS 194)
                          #   staffing.py: the reading's staff lines (prompt v9) priced by rule:
                          #   price table wins, call-off as written, shifts only for a committed
                          #   team, months from the line, helpdesk only when asked for, chatbot
                          #   complex only with the buyer's systems (OPEN_QUESTIONS 162)
      reports/            # PDF report (reportlab) + Excel BoQ (openpyxl) from one ReportData
      outcomes.py         # bid results + calibration report
      documents/ extraction/ retrieval/ mapping/ reports/ templates/   # later milestones
    llm/                  # LLMClient protocol, AnthropicClient, FakeClient; prompts/*.md (versioned)
    jobs/                 # Huey instance and tasks
  seeds/                  # taxonomy/v1..v2, catalog/v1..v9, rate_cards/, parameters/,
                          #   quick_estimate.yaml (plain features/questions for simple mode)
                          #   + `topics`: the form asks one topic at a time (build, users, hosting,
                          #   support, contract) on both paths; every question / number has one
                          #   (OPEN_QUESTIONS 177); the EMD is read, never shown (`Fact.hidden`)
                          #   + `commonly_needed`: the fixed 8 features the features screen asks
                          #   about when the description did not mention them (OPEN_QUESTIONS 150)
                          #   + `industry_suggestions`: the AI reading names up to 10 modules
                          #   this kind of software usually has (any industry), checked in code
                          #   (`tender.industry_suggestions`), offered unticked in place of that
                          #   fixed list, each priced by the engine (POST /quick-estimate/
                          #   suggestion-prices); never basics (OPEN_QUESTIONS 207)
                          #   prompt v10 `ready_made`: "ready products are common for this kind",
                          #   shown above the build-type prices, words only (OPEN_QUESTIONS 209)
                          #   + `industries`: the manual form's "What is it for?" (13 + something
                          #   else), each with its popular features offered unticked and priced,
                          #   with a level; `feature_groups`: browse all by purpose (OPEN_QUESTIONS 212)
                          #   + `cms_built_in`: on a CMS build, what the CMS already has is
                          #   set up, not built (basic, one module; OPEN_QUESTIONS 154)
                          #   + `scope`: what else a feature needs, as catalog blocks at a level
                          #   (every value has a `source`; `placeholder` = uncalibrated)
                          #   prices follow what is built (feature levels), never the client type
                          #   catalog v6+: each component's effort `evidence` and `source_era`;
                          #   AI savings on pre_ai data (never ai_assisted); unknown counts as
                          #   pre_ai from parameters v18 (hours calibrated on pre-AI projects)
                          #   parameters v19+: `reuse` shrinks the crud / ui_design shares
                          #   for build_type cms or framework (placeholder priors); hard-problem
                          #   components get a wider range and no reuse; penalty reserve only
                          #   with a penalty clause
                          #   parameters v20+ (OPEN_QUESTIONS 144): review and tests follow
                          #   the reuse (`reuse.follow_tasks`); `effort_caps` on review,
                          #   pre-build and architect; AI review split like review work;
                          #   rate card v9: audited cloud/SSL rates, free DV certificate;
                          #   caps by project size (review, pre-build, architect; the
                          #   in-between sizes are written-out midpoints, a guess);
                          #   the whole AI saving is always passed on (`ai_passthrough` forced to
                          #   all; was a company setting, OPEN_QUESTIONS 173, 227)
                          #   parameters v21+: the range widens with project size
                          #   (model_spread_by_size, placeholder; OPEN_QUESTIONS 153)
                          #   parameters v22+: support level 24x7_on_call (office hours +
                          #   on call); stated support staff are the least support labour
                          #   (maintenance.support_staff.v1, OPEN_QUESTIONS 157)
                          #   parameters v24+: 4.0 people per staffed round-the-clock seat;
                          #   staff for some months or as round-the-clock seats priced by
                          #   maintenance.onsite.v2 / support_staff.v2 (OPEN_QUESTIONS 162)
                          #   parameters v25+: a small site (one server on the small rate) runs
                          #   its database on that server: no managed database, no monitoring
                          #   fee on AWS's free tier (hosting.small_site, OPEN_QUESTIONS 165);
                          #   with rate card v10, hosting is one line a year (hosting.bundle.v1,
                          #   a monthly rate by provider / plan / load band) and upkeep one line
                          #   (maintenance.upkeep.v1); onsite developers / PM named in a staff
                          #   line do the upkeep / O&M PM (`covers`); annual audit from year 2;
                          #   year 1 leaves out the hypercare weeks (OPEN_QUESTIONS 166)
                          #   parameters v26+ (OPEN_QUESTIONS 171): a site whose load fits one
                          #   server (about 400 online at once, `single_max_vcpus`) at 99.5% uptime
                          #   runs on one server, not two + a load balancer
                          #   (`hosting.small_site.single_for_sla`); servers follow load and uptime,
                          #   never the feature count; the form asks the uptime (details) and,
                          #   optionally, the people online at once (`overrides.peak_concurrent_users`);
                          #   with rate card v11, hosting is priced by the actual number online on a
                          #   straight line between price points (`hosting.bundle.price_points`,
                          #   `hosting.bundle.v2`), not at the middle of the load band
                          #   parameters v27+ (OPEN_QUESTIONS 179): on lean delivery the handover
                          #   (exit management) is min(band days, `lean.exit_share_of_build_pd` ×
                          #   build); a deadline too short to build in is priced at the fastest
                          #   possible time (`engine.core.schedule`, `quick.service.at_fastest`),
                          #   shown beside the deadline (POST /quick-estimate/schedule)
                          #   parameters v28+ (OPEN_QUESTIONS 180): on small and small-to-medium
                          #   projects the tests task is at most `effort_caps.tests_max_share_by_size`
                          #   (0.40) of the tested work; medium and larger unchanged
                          #   parameters v29+ (OPEN_QUESTIONS 182): a deadline longer than the
                          #   build is built in the natural time (no stretched management);
                          #   helpdesk seats on a line by users (`helpdesk_seats_points`);
                          #   quick config `scale.curve`: online at once, chatbot questions and
                          #   documents follow the users (a typed count priced as typed); both
                          #   forms show the same users block (`UsersNumbers` in parts.tsx)
                          #   near a size-tier edge the standard blocks are priced between two
                          #   sizes (`sizing.tier_blend_share`, component `size_mix`); the
                          #   pre-build cap counts work at the usual complexity (OPEN_QUESTIONS 183)
                          #   and lean delivery (PM, hypercare, handover), training sessions and
                          #   hypercare weeks move in a line across the edge (`size_blend`, 184)
                          #   parameters v30+ (OPEN_QUESTIONS 187): near a size edge the caps by
                          #   size (`effort_caps.blend_across_size_edge`) and the range's spread
                          #   sit between the two sizes'; test servers 1 -> 2 in a line; load
                          #   testing comes in with the users (scale question `ramps`)
                          #   parameters v23+ (OPEN_QUESTIONS 160): the shared model factor is
                          #   centred on its median (widens, no P50 lift) and is a range driver;
                          #   size-band values blend across band edges (size_band_blend_share)
                          #   parameters v31+ (OPEN_QUESTIONS 192): front end only (question
                          #   `build_part`, questionnaire `build_layers`): every task × its
                          #   `layers.task_factor_by_layers` factor (formula component_labour.v8);
                          #   the answer hides and fixes the server questions (hide_when +
                          #   default_by = forced) and drops blocks (option `drop_components`)
                          #   parameters v32+ (OPEN_QUESTIONS 195): who builds it (question
                          #   `builder`, questionnaire `builder_type`): every person's day rate
                          #   × `builder.rate_factor_by_builder` (role_rate.v2); mid-size firm = 1
                          #   only what is needed (196): firewall above 10,000 users, SMS its own
                          #   choice, question `payment_terms` (advance = no delay, working_capital
                          #   .v3; milestones = tender, adds the requirement study)
                          #   parameters v33+ (OPEN_QUESTIONS 228): complexity multipliers are
                          #   COCOMO II.2000 CPLX (0.87 / 1.00 / 1.34 / 1.74); effort caps and the
                          #   upkeep split name the published figures they were checked against
                          #   parameters v34+ (OPEN_QUESTIONS 229): the team follows the work
                          #   (`staffing`, engine/staffing.py, formula staffing.v1): a role joins
                          #   when an answer needs it, with a booking's worth of work, or when
                          #   booking it is no dearer; else its work × slowdown goes to its
                          #   fallback; the project manager likewise, else the team's lead
                          #   parameters v35+ (OPEN_QUESTIONS 231): a hardware list for own servers
                          #   (`hardware`, services/hosting/hardware.py, hardware_list.v1), sized
                          #   by load and uptime; optional (hosting on_prem, or question
                          #   hardware_list = client_buys); from the saved inputs, a list only
                          #   parameters v36+ (OPEN_QUESTIONS 232): own server room pays no rack
                          #   rent (`on_prem.rent_racks`); power, cooling, room = client's own cost
                          #   parameters v37+ / rate card v12 (OPEN_QUESTIONS 233): own servers priced
                          #   from the hardware list (`hardware.priced`, on_prem_lines), servers by size,
                          #   app and database share a 16-core server when they fit; yearly licences
                          #   question `hardware_supply` (own server room only): the client may buy the
                          #   hardware itself, list shown out of the price (OPEN_QUESTIONS 235)
                          #   parameters v38+ (OPEN_QUESTIONS 236): a small site on own servers is one
                          #   server, firewall and switch at 99.5% (`small_site.single_on_own_servers`);
                          #   bought hardware, its AMC and licences carry a reseller's margin
                          #   (`commercial.bought_items`, formula commercial.margin.v2)
                          #   parameters v39+ / rate card v13 (OPEN_QUESTIONS 238): day rates from
                          #   Gujarat's 2026 IT manpower rate contract (Tier II = mid-size firm,
                          #   ÷ 22 days ÷ 1.15); builder factors large 2.5 (freelancer 0.5); the team
                          #   follows who builds it (`staffing.by_builder`: not_booked / always_booked /
                          #   min_booking_pd / book_when_cheaper), go-live and support work too
                          #   (`components.staffed`); an unanswered build type is `framework` for a
                          #   freelancer or small company (question `build_type` default_by)
                          #   + Azure / Google Cloud (question `cloud_provider`, rate card v13
                          #   items and price points, OPEN_QUESTIONS 240); hardware the department
                          #   buys answers `hardware_supply` (client_provided `also`, 239)
                          #   catalog v7+: a tech-stack `section` per component (core, web,
                          #   mobile, ecommerce, ai_ml, security, ...) and a `url` per source
                          #   catalog v8 (OPEN_QUESTIONS 213): + 15 industry blocks (education,
                          #   health, finance, ...) from published hours; an `industries` module
                          #   names its `block` (the custom feature's `catalog_key`)
                          #   catalog v9: v8 with registration_empanelment renamed "Online forms
                          #   and applications" (OPEN_QUESTIONS 229)
                          #   a feature's `skip_at` leaves out blocks at a level, listed on the
                          #   quote as not needed (basic online forms: no master data, OQ 230)
  migrations/             # Alembic
  tests/                  # api/, core/, engine/ (unit, property, golden/*.yaml + *.expected.json)
                          #   fixtures/srs/: synthetic requirement documents + expected-results manifests
                          #   fixtures/readings/: saved tender readings (production-path back-test),
                          #   fixtures/review_form/: what the review form sent for them (parity)
                          #   fixtures/readings_v9/: the same readings + staff lines entered by
                          #   hand (no AI re-read, OPEN_QUESTIONS 162); readings_v10/: + the
                          #   stated counts read in code, the back-test's default (194)
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
| Install or update the Ubuntu server (pull, install, migrate, seed, build, restart) | `bash deploy/update.sh` on the server (first install: `docs/DEPLOY.md`) |
| Apply migrations | `make migrate` |
| Load seed data (taxonomy, catalog, rate card, parameters, demo users + demo project) | `make seed` |
| All tests (pytest + frontend typecheck/lint) | `make test` |
| Backend tests only | `make test-backend` (or `cd backend && uv run pytest`) |
| Lint / type-check (ruff, ruff format --check, mypy, eslint, prettier) | `make lint` |
| Auto-format | `make format` |
| Regenerate OpenAPI JSON + TS types | `make openapi` |
| Regenerate golden expectations (intentional engine change only) | `make golden` |
| New migration after model change | `make migration m="describe change"` |
| Back-test against real projects. First the **production path** (headline): the 8 tenders with a saved reading in `backend/tests/fixtures/readings_v10/` (stand-in model readings + staff lines entered by hand; `--readings` picks another folder), priced through the review form's pre-fill as an upload is (OPEN_QUESTIONS 161). Then the **legacy path, not the production path** (the benchmark file's hand-mapped scope), with and without AI tools (contracts up to `pre_ai_until` judged without): error, bias (ours / published), P10-P90 coverage and band hits by size and client type, in one run / fit the smooth size curve (factor by feature points) | `cd backend && uv run python -m app.cli backtest --country india [--as-of YYYY-MM-DD] [--layers] [--calibrate]` |
| Benchmark tender readings (round 3): `reading:` blocks and `onsite_staff` in `backend/seeds/benchmarks/india.yaml`; a project left out names its `exclude_rule` (rules at the top of each benchmark file, OPEN_QUESTIONS 155); the reading files and scripts in `data/benchmark_readings/` (not committed) | see OPEN_QUESTIONS 153, 155; PBD control log 156 |
| The catalog as one plain table to read (a view only, never priced from): `docs/CATALOG.md` + `data/catalog.xlsx`; run again after a catalog change | `cd backend && uv run python -m app.cli catalog-table [--version v7]` |
| Check the email (SMTP) settings: send one test email | `cd backend && uv run python -m app.cli test-email you@example.com` |
| Show market prices (published contracts) on results again (off: they fluctuate too much, OPEN_QUESTIONS 127) | `show_market_prices:` in `backend/seeds/quick_estimate.yaml` |
| Switch a country on/off in the app | `enabled:` under `countries:` in `backend/seeds/quick_estimate.yaml` (the US is off for now) |

## Coding conventions

- Python: type hints everywhere; `ruff` + `mypy --strict` clean; Pydantic models at every boundary.
- Engine (`services/engine`, `services/hosting`): small pure functions; every function documents its formula in its docstring; register each formula id in `engine/formulas.py`; deterministic arithmetic in `Decimal`, rounded to integer paise (`ROUND_HALF_UP`) at each cost line; floats only inside Monte Carlo.
- No magic numbers in code: rates, multipliers, thresholds and defaults live in `backend/seeds/` YAML with a `source` (`placeholder` until calibrated). Any placeholder used marks the estimate **uncalibrated**.
- Reference versions are immutable. To change a price or parameter, add a new version file (e.g. `rate_cards/v2.yaml`) — never edit a published version; `make seed` warns if a stored version differs from its file.
- New engine line types: register the formula in `engine/formulas.py`, build the line through `PricingContext.builder(...)` so the trace is recorded, add a unit test, then `make golden` and review the diff.
- Every tenant query goes through `app/core/tenancy.py` helpers (`scoped`, `get_owned`) so `org_id` is always applied.
- Money: integer paise in the DB and API (`*_paise` fields). Rate amounts are `Decimal` strings in major units of their currency.
- LLM output is validated against Pydantic schemas; document text is fenced in prompts and never treated as instructions.
- Tests never call a real LLM: `tests/conftest.py` blanks `ANTHROPIC_API_KEY`; use `set_llm_client(FakeClient(...))`.
- To try the AI paths in the running app without the API key: `LLM_PROVIDER=claude_cli` uses the
  local `claude` command and the developer's own Claude account (development only, OPEN_QUESTIONS 234).
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
5. At the end of a milestone: its acceptance criteria from brief Section 12 are met. **Commit only after the user has checked the work in the running app and explicitly says to commit.**
