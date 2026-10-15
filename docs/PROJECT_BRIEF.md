# Aakalan — Project Brief for the Coding Agent

> Working name: **Aakalan** (आकलन, "estimation"). Rename freely; keep it consistent across the repo.
> This file is the single source of truth for WHAT we are building and WHY. Keep it at `docs/PROJECT_BRIEF.md`.

---

## 0. Instructions for the agent (read first)

1. Read this whole brief before writing any code.
2. Create two files at the repo root:
   - **`AGENTS.md`** — the canonical guide for any coding agent: project summary (10 lines), architecture rules (Section 3, verbatim), tech stack, repo layout, exact commands (install, run, test, lint, migrate), coding conventions, and the definition of done. Keep it under ~200 lines; link to `docs/PROJECT_BRIEF.md` for detail instead of copying it.
   - **`CLAUDE.md`** — first line `@AGENTS.md` (imports it), then only Claude-specific notes (e.g. "run `make test` before saying a task is done"). Do not duplicate AGENTS.md.
3. Move this brief to `docs/PROJECT_BRIEF.md`. Create `docs/OPEN_QUESTIONS.md` listing anything unclear, each with the default you chose. Do not stop to ask; proceed with the default.
4. Build milestone by milestone (Section 12). Finish each milestone's acceptance criteria and tests before starting the next. If the repo uses git, commit at the end of each milestone.
5. Keep `AGENTS.md` updated whenever commands, structure or conventions change.

---

## 1. Problem statement

Government departments, PSUs and non-technical companies don't know what a software project should cost. Traditionally they hire consulting firms (TCS, Infosys, Wipro, etc.) that run weeks of sessions — requirements documents, scoping sessions, workshops, presentations, commercials, technical architecture, compliance and cyber review — and price the work as **people × months × rate**.

In the AI era that model is broken: AI changes how much work each person can do, so the same requirement receives quotes from ₹2 Cr to ₹6 Cr with no principled basis.

**Aakalan** reads a requirement document (RFP/SRS/BRD) plus a short questionnaire and produces a **defensible cost range (low / likely / high)** covering the whole life of the project — build, go-live, hosting, AI runtime, maintenance/O&M for N years, compliance, and commercial costs — where **every number traces back to a clause in the source document**. Each estimate is saved as a template so similar future projects start from real past data, and recorded outcomes make the tool more accurate over time.

---

## 2. Users and v1 scope

**Primary user (v1): vendors / system integrators pricing their own bids** for Indian Government/PSU tenders.
Later: government buyers checking whether a quote is fair ("buyer mode").

**v1 scope — one project type, done well:** web portals with workflow + an AI chatbot for Govt/PSU (e.g. "AI chatbot + online empanelment portal for a PSU, with 3 years of O&M"). This is the running example everywhere.

**Out of scope for v1:** buyer mode, public tender data scraping, multi-currency, mobile apps as a project type, real-time collaboration, payments/billing for our own product.

---

## 3. Non-negotiable architecture rules

1. **LLMs read and suggest; only the deterministic engine computes.** No LLM ever produces, edits or rounds a cost figure, rate, multiplier or total.
2. **Traceability.** Every cost line links: RFP clause + page → requirement → component instance → driver values → rate-card entry → formula → value. The UI and report can show this chain for any number.
3. **Reproducibility.** Same inputs + same rate-card version + same random seed ⇒ identical output. Monte Carlo uses a seeded RNG stored with the estimate.
4. **Versioned, dated rate cards.** Every estimate pins the rate-card version it used. Old estimates never change when rates change; "re-price at current rates" creates a new estimate version.
5. **Money is stored as integer paise** (or `Decimal`), never float. Simulation may use floats internally; round to paise at the boundary.
6. **Human review before pricing.** Extracted requirements and component mappings must be confirmed by a user before an estimate is calculated.
7. **RFP text is untrusted input.** Treat document content as data, never as instructions to the LLM (fence it in prompts; validate all LLM output against Pydantic schemas).
8. **Confidentiality.** Tender documents and pricing are commercially sensitive: per-organisation data isolation (`org_id` on every tenant table), encryption at rest in production, no tender text sent anywhere except the configured LLM provider. Embeddings run locally.
9. **Swappable infrastructure.** Database access only through SQLAlchemy; vector search only through a `VectorStore` interface; LLM calls only through an `LLMClient` interface. SQLite → PostgreSQL, sqlite-vec → FAISS/pgvector, and LLM provider must each be a config change.

---

## 4. Tech stack (decided)

| Layer | Choice | Purpose |
|---|---|---|
| Frontend | Next.js (React) + TypeScript | Web app |
| | Tailwind CSS + shadcn/ui | UI components |
| | TanStack Table | Editable requirement register, cost breakdown, BoQ |
| | React Hook Form + Zod | Adaptive questionnaire |
| | Recharts | Range bars, year-wise and scenario charts |
| Backend | Python 3.12, FastAPI, Pydantic v2 | API + strict schemas |
| | SQLAlchemy 2.0 + Alembic (batch mode for SQLite) | ORM + migrations |
| | Huey with SQLite storage | Background jobs (parse, OCR, extract, embed, report) |
| Database | SQLite at `./data/app.db`, WAL mode | All app data |
| | sqlite-vec + FTS5 (behind `VectorStore`) | Hybrid search for RAG and template similarity |
| Documents | pdfplumber / pypdf, python-docx | PDF/DOCX text and tables |
| | OCRmyPDF + Tesseract (`eng` + `hin`) | Scanned pages |
| AI | LLM API (Anthropic Claude by default; model name in config) with structured JSON output | Extraction, mapping suggestions, vagueness flags, pre-bid queries, narrative |
| | sentence-transformers, local multilingual model (default BGE-M3; configurable) | Embeddings, on our own server |
| | Optional local reranker (bge-reranker) | Better retrieval |
| Engine | Plain Python + NumPy | Formulas, Monte Carlo, scenarios |
| Reports | Jinja2 + WeasyPrint; openpyxl | PDF report; Excel BoQ |
| Auth | JWT + argon2; roles: admin, estimator, finance, viewer | Margin visible only to finance/admin |
| Ops | Docker + docker-compose, Caddy, Litestream → S3, Sentry | Deploy, HTTPS, backups, errors |
| Quality | pytest, ruff, mypy; ESLint + Prettier; Playwright (later) | Tests and lint |

**Licence rule:** do not use AGPL libraries (e.g. PyMuPDF) without a commercial licence.

**SQLite settings on every connection:**
```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;
```
Load sqlite-vec via a SQLAlchemy `connect` event. Use the official `python:3.12-slim` Docker image (some local Python builds can't load SQLite extensions).

**Data directory (gitignored, mounted as a Docker volume):**
```
./data/
  app.db
  huey.db
  uploads/<org_id>/<project_id>/
  reports/<org_id>/<project_id>/
  models/            # local embedding / reranker models
```

**Deployment target:** AWS ap-south-1 (Mumbai). Stage 1: one EC2 instance, `./data` on an encrypted EBS volume (never EFS), S3 for uploads/reports/Litestream backups, Secrets Manager for keys. Stage 2 (later): RDS PostgreSQL + pgvector, ECS Fargate, SQS. Write nothing that blocks Stage 2.

---

## 5. Repository layout

```
aakalan/
  AGENTS.md  CLAUDE.md  README.md  Makefile  docker-compose.yml  .env.example
  docs/  PROJECT_BRIEF.md  OPEN_QUESTIONS.md  ARCHITECTURE.md
  backend/
    app/
      api/            # FastAPI routers
      core/           # config, security, logging, db session, sqlite pragmas
      models/         # SQLAlchemy models
      schemas/        # Pydantic schemas
      services/
        documents/    # parsing, OCR, clause chunking
        extraction/   # LLM extraction, vagueness detection, pre-bid queries
        retrieval/    # VectorStore interface, sqlite-vec + FTS5 hybrid, reranker
        mapping/      # requirement -> component suggestions
        engine/       # deterministic cost engine (NO LLM imports allowed here)
        hosting/      # infra sizing -> cloud line items
        reports/      # PDF + Excel
        templates/    # save / match / adapt templates
      llm/            # LLMClient interface + Anthropic implementation + prompts
      jobs/           # Huey tasks
    seeds/            # component catalog, rate cards, AI factors (YAML)
    migrations/       # Alembic
    tests/
      engine/golden/  # golden estimates
      extraction/     # labelled RFP excerpts
  frontend/           # Next.js app
  data/               # gitignored
```

Enforce with a test: `services/engine` must not import anything from `llm/`.

---

## 6. Domain model (core tables)

All tenant tables carry `org_id`. Use UUID primary keys, `created_at`, `updated_at`.

- **Organisation, User** (role).
- **Project**: name, buyer_type (govt/psu/private), domain, mode (vendor/buyer), status.
- **Document**: project_id, filename, kind (rfp/annexure/corrigendum/prebid_reply), pages, sha256, storage_path, parse_status.
- **Chunk**: document_id, clause_ref, page_from, page_to, heading, text; FTS5 index; vector row in sqlite-vec.
- **Requirement**: project_id, code (REQ-001), text_normalised, category (functional / NFR / integration / compliance / commercial / O&M / manpower), clarity_score (1–5), status (extracted / confirmed / rejected / edited), source chunk ids (clause + page).
- **Flag**: requirement_id or chunk_id, type (missing_quantity / unnamed_scope / weasel_words / conflict / open_ended), message, suggested_prebid_query.
- **QuestionnaireAnswer**: project_id, key, value, source (user / default).
- **CatalogComponent**: key, name, category, task_mix (share of effort by task type), base_effort_pd {S, M, L}, applicable drivers, version.
- **ComponentInstance**: project_id, catalog_component_id, size, driver values (JSON), linked requirement ids, confirmed_by.
- **RateCard** (version, effective_date, source, status) → **RateItem** (kind: role / cloud_sku / llm_token / gpu_hour / licence / audit_fee / bank_charge / other; key; unit; amount_paise; currency; region; source_url).
- **Estimate**: project_id, version, rate_card_version, seed, inputs_snapshot (JSON), p10/p50/p90 totals, confidence, created_by, frozen (bool).
- **CostLine**: estimate_id, stage, bucket, year (0 = build), component_instance_id (nullable), formula_id, inputs (JSON), low/likely/high paise, requirement ids.
- **Assumption**: estimate_id, text, value, overridden (bool).
- **Template**: from estimate; normalised requirement register, components, metadata (domain, buyer_type, scale band, hosting, ai), embedding.
- **Outcome**: project_id, bid_result (won/lost/withdrawn), our_price, l1_price, actual_effort_pd, actual_costs (JSON), notes.
- **AuditLog**: who, what, when, before/after.

---

## 7. Estimation engine specification

### 7.1 Component cost
For each component instance *i*:
```
labour_i = Σ_task  base_effort_pd(size) × task_share × M_complexity × M_nfr × (1 − ai_saving_task) × rate_role(task)
cost_i   = labour_i + non_labour_i      (infra, tokens, licences, audits attributable to i)
```
- **Complexity multipliers** (seed defaults, calibrate later): low 0.7, medium 1.0, high 1.5, very high 2.2.
- **NFR multipliers**: uptime SLA, security level, number of languages, accessibility (GIGW), concurrency band.
- **AI productivity factor by task type** (seed defaults, editable):
  documentation 0.6 · CRUD/boilerplate 0.5 · tests 0.4 · architecture 0.15 · integration with govt systems 0.1 · UAT/audit remediation/reviews 0.05 · PM/meetings 0.0
  Plus a per-project "team AI maturity" input (low / medium / high) that scales these.

### 7.2 Three-point values and range
- Each component and bucket gets optimistic / likely / pessimistic values. The spread is set by clarity score, template-match strength, integration unknowns, AI-volume uncertainty, schedule compression, and O&M length.
- Combine with a seeded Monte Carlo (PERT or triangular, default 10,000 runs). Output **P10 (low), P50 (likely), P90 (high)** and a confidence label (high / medium / low) derived from average clarity, template match and rate-card freshness.
- Report the top 3 drivers of the spread ("O&M staffing and integrations contribute most of the range").

### 7.3 Timeline
- Compute **natural duration** from total build effort and a sensible max team size for the project size.
- If the user's deadline is shorter: apply a **compression multiplier** (default curve 1.0 at natural → 1.4 at 60% of natural) and widen the range; below ~50% of natural, return **"not feasible"** with a phased-delivery suggestion instead of a number.
- If longer: add programme overhead (PM, environments) for the extra months; cost does not fall linearly.
- Produce a **manpower view** (roles × months) as an OUTPUT, because many tenders require it.

### 7.4 Run costs per year (years 1..N of O&M)
- **Hosting sizing** (`services/hosting`): from users, peak concurrency, document volume, chatbot queries/day and uptime SLA → architecture pattern (single / HA / HA + DR) → line items (compute, managed DB, storage, backups, data transfer, load balancer, monitoring, DR) → priced from the rate card. Support AWS (default, ap-south-1), a MeitY-empanelled Indian cloud and on-prem as scenarios. Include storage growth per year, USD→INR conversion with a forex buffer, and reserved vs on-demand options.
- **AI runtime**: queries/day × tokens/query × token price, or GPU-hours if self-hosted.
- **Maintenance**: bottom-up — helpdesk by support SLA (8×5 / 24×7), bug-fix and patching effort by system size, upgrades, annual re-audit, SSL/domain, change-request pool, mandated onsite staff. Show the industry rule of thumb (15–25% of build per year) beside it as a sanity check and flag large differences.
- **Escalation**: salary and price escalation per year (default 8%, configurable).

### 7.5 Commercial layer
EMD lock-up cost, PBG bank charges, working capital from the milestone payment schedule, penalty/LD reserve from SLA slabs, contingency (from overall clarity), margin (finance role only), GST (default 18% on IT services; configurable per line).

### 7.6 Scenarios
Toggles re-price instantly and show side by side: cloud vs on-prem; AWS vs Indian cloud; LLM API vs self-hosted GPU; open source vs licensed; deadline variants.

---

## 8. Cost taxonomy (buckets)

- **Pre-build**: discovery/requirement study, solution architecture, UI/UX.
- **Build**: module development, integrations, AI/ML work (RAG, prompts, evaluation sets, guardrails), data migration, testing (functional, UAT support, load, VAPT), documentation.
- **Go-live**: CERT-In empanelled security audit + re-audit, STQC/other certification where mandated, training (incl. travel), hypercare.
- **Run (per year)**: hosting, backups, DR, AI runtime, licences, helpdesk, onsite resources, change-request pool, patching, annual re-audit, SSL/domain, escalation.
- **Programme**: project management, steering meetings, MIS reports, travel.
- **Commercial**: EMD/PBG, working capital, penalty reserve, exit management, contingency, margin, GST.

Store the taxonomy as seed data, not hard-coded enums, so buckets can be added without a release.

---

## 9. Document pipeline and RAG

1. **Parse**: pdfplumber/pypdf for digital PDFs, python-docx for DOCX; detect pages with no text layer and OCR them (OCRmyPDF, `eng+hin`). Keep page numbers.
2. **Chunk by structure**: split on clause numbering (e.g. `4.3.2`) and headings, not fixed token windows. Every chunk keeps `clause_ref`, page range, heading path.
3. **Index**: FTS5 for keywords (clause numbers, "EMD", "PBG", "LD", "SLA") + sqlite-vec embeddings. **Hybrid retrieval** (reciprocal rank fusion) + optional rerank.
4. **Extract per field** (Section 3 of extraction checklist below): for each field, retrieve relevant chunks, ask the LLM for JSON matching a Pydantic schema, require `clause_ref` + `page` for every value; reject output without citations.
   Fields: functional modules, user roles and counts, volumes and concurrency, integrations, languages, AI features, hosting mandate, SLAs and penalties, security/compliance clauses, timeline and milestones, warranty/O&M/AMC period, manpower clauses, payment terms, financial-bid (BoQ) format, EMD/PBG/LD, eligibility, exit and IP clauses.
5. **Coverage check**: report which RFP sections produced no requirement, so nothing is silently skipped.
6. **Vagueness and conflicts**: flag missing quantities, unnamed scope, weasel words, conflicting clauses, open-ended obligations; draft a pre-bid query citing the clause for each.
7. **Template RAG**: for each confirmed requirement, retrieve similar requirements from past templates and how they were mapped and sized; the LLM suggests component + size; the user confirms.
8. **Knowledge-base RAG** (later milestone): compliance guidance and a library of past pre-bid queries.
9. **"Ask the RFP"** chat (later milestone): answers must cite clause and page.

Track tokens and LLM cost per project; store prompts as versioned files under `llm/prompts/`.

---

## 10. API (sketch)

```
POST   /auth/login
POST   /projects                         GET /projects  GET /projects/{id}
POST   /projects/{id}/documents          (upload; enqueues parse job)
GET    /projects/{id}/jobs/{job_id}
GET    /projects/{id}/requirements       PATCH /requirements/{id}   POST /projects/{id}/requirements/confirm
GET    /projects/{id}/flags              GET /projects/{id}/prebid-queries
GET    /projects/{id}/questionnaire      PUT /projects/{id}/questionnaire
GET    /projects/{id}/components         (suggested)  PUT /projects/{id}/components (confirmed)
GET    /projects/{id}/similar-templates
POST   /projects/{id}/estimates          (calculate; returns new version)
GET    /estimates/{id}                   GET /estimates/{id}/lines/{line_id}/trace
POST   /estimates/{id}/scenarios
GET    /estimates/{id}/report.pdf        GET /estimates/{id}/boq.xlsx
POST   /estimates/{id}/save-as-template
POST   /projects/{id}/outcome
GET/POST /admin/rate-cards  /admin/catalog
```

---

## 11. Frontend screens

1. Login · Project list
2. New project (mode, domain, buyer type, rate-card version)
3. Upload documents + parsing progress
4. **Requirement review** — editable table with clause/page links; confirm/reject/edit; flags inline
5. **Questionnaire** — adaptive, highest range-impact questions first, defaults shown
6. **Component mapping** — suggested components with reasons and similar-template hints; confirm/resize
7. **Estimate** — P10/P50/P90 headline, confidence, top range drivers, breakdown by stage/bucket/year, manpower view, click any number → trace panel
8. Scenarios side by side
9. Pre-bid queries (copy/export)
10. Export PDF / Excel · Save as template · Record outcome
11. Admin: rate cards (versions, effective dates), component catalog, AI factors

---

## 12. Milestones (build in this order)

**M0 — Scaffolding.** Monorepo, AGENTS.md, CLAUDE.md, docs, Makefile (`make dev`, `make test`, `make lint`, `make migrate`, `make seed`), docker-compose, SQLite with pragmas, Alembic, auth with roles, health endpoint, Next.js shell with login.
*Done when:* `make dev` runs both apps; `make test` passes; a user can log in.

**M1 — Engine first (no AI, no documents).** Domain models; seed component catalog (~30 components for the portal + workflow + chatbot type), rate card v1, AI factors, taxonomy — every seeded number marked `source: placeholder` and the report shows "uncalibrated" while any placeholder is used. Deterministic engine: component costs, timeline, run costs per year incl. hosting sizing, maintenance, commercial layer, Monte Carlo P10/50/90, scenarios, traceability. Manual entry of requirements and components via API and a simple UI.
*Done when:* 3 golden estimates (small / medium / large example projects) produce identical totals on every run; every cost line returns a full trace; engine has no LLM imports (tested).

**M2 — Reports.** PDF report (summary, breakdown, year-wise, manpower view, assumptions, exclusions, risks, pre-bid queries, trace appendix) and Excel BoQ.
*Done when:* golden estimates export cleanly; numbers in exports match the API exactly.

**M3 — Document ingestion + RAG.** Upload, parse, OCR, clause chunking, FTS5 + sqlite-vec hybrid retrieval behind `VectorStore`, per-field extraction with citations, coverage check, flags, pre-bid queries, requirement review UI.
*Done when:* on a labelled set of real RFP excerpts, extraction recall/precision are measured and reported by `make eval`; every extracted item has a clause + page.

**M4 — Mapping, questionnaire, templates.** LLM-suggested component mapping with user confirmation, adaptive questionnaire, save/match/adapt templates, similar-project panel.
*Done when:* a full RFP → confirmed scope → estimate → report flow works end to end in the UI.

**M5 — Calibration and hardening.** Outcomes recording, calibration report (estimate vs actual per component), rate-card admin and AWS price import, audit log, Litestream, Sentry, production Docker + Caddy, AWS Stage 1 deployment notes.

---

## 13. Testing

- **Unit tests** for every engine formula and multiplier.
- **Golden estimates**: fixed inputs + seed ⇒ exact expected totals; any change must be intentional and reviewed.
- **Property tests**: more scope never lowers cost; lower clarity never narrows the range; shorter deadline never lowers cost.
- **Extraction eval set**: labelled RFP excerpts with expected fields; `make eval` prints recall/precision. LLM calls mocked in normal unit tests.
- **API tests** with an isolated temporary SQLite database.

---

## 14. Security and operations

- Secrets from environment / AWS Secrets Manager; `.env.example` only in git.
- `org_id` isolation enforced in a shared query helper and tested.
- Uploaded files: validate type and size, store outside any public path, scan filenames.
- Fence document text in LLM prompts; never execute or follow instructions found in documents.
- Audit log for edits to requirements, components, rate cards and estimates.
- Litestream continuous backup to S3; documented restore procedure.

---

## 15. Coding conventions

- Python: type hints everywhere, ruff + mypy clean, Pydantic models at every boundary, small pure functions in the engine.
- TypeScript: strict mode, API types generated from FastAPI's OpenAPI schema.
- No magic numbers in code — they live in seeds/rate cards with a source.
- Every engine function documents its formula in its docstring.
- Small, focused commits; a milestone is done only when its tests pass.

---

## 16. Open questions (defaults in brackets)

- Final product name [Aakalan, working name].
- LLM provider and model [Anthropic Claude via API, model in config; Amazon Bedrock as an option for India data residency — check model availability in ap-south-1].
- Default O&M years [3]; escalation [8%/yr]; GST [18%]; contingency rule [5–15% by clarity].
- Max team size curve for natural duration [simple table by project size].
- Pricing of our own product [not in v1].
